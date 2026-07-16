from collections import defaultdict
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command


class ProductVariantCombineWizard(models.TransientModel):
    _name = "product.variant.combine.wizard"
    _description = "Combine Products into One Product Template"

    new_template_name = fields.Char(string="New Product Template", required=True)
    product_ids = fields.Many2many(
        comodel_name="product.product",
        relation="product_variant_combine_wizard_product_rel",
        column1="wizard_id",
        column2="product_id",
        string="Products to Combine",
        required=True,
    )
    base_product_id = fields.Many2one(
        comodel_name="product.product",
        string="Base Product",
        required=True,
        help=(
            "The new template copies its common template-level configuration "
            "from this product."
        ),
    )
    variant_attribute_name = fields.Char(
        string="Variant Attribute",
        required=True,
        help=(
            "Enter the attribute that will distinguish the selected products, "
            "for example Color, Size, Capacity, or Model."
        ),
    )
    preserve_sale_prices = fields.Boolean(
        string="Preserve Sale Prices",
        default=True,
        help=(
            "Uses the lowest current sale price as the new template price and "
            "stores the difference on each generated attribute value."
        ),
    )
    migrate_vendor_pricelists = fields.Boolean(
        string="Preserve Vendor Pricelists",
        default=True,
        help=(
            "Moves variant-specific vendor records and copies template-wide vendor "
            "records as variant-specific records on the new template."
        ),
    )
    archive_empty_templates = fields.Boolean(
        string="Archive Empty Source Templates",
        default=True,
        help=(
            "Archives a source template only when it has no remaining variants, "
            "including archived variants."
        ),
    )
    line_ids = fields.One2many(
        comodel_name="product.variant.combine.wizard.line",
        inverse_name="wizard_id",
        string="Variant Values",
        copy=False,
    )

    @api.model
    def default_get(self, field_names):
        values = super().default_get(field_names)
        if self.env.context.get("active_model") != "product.product":
            return values

        active_ids = list(dict.fromkeys(self.env.context.get("active_ids", [])))
        products = self.env["product.product"].with_context(active_test=False).browse(
            active_ids
        ).exists()
        if not products:
            return values

        if "product_ids" in field_names:
            values["product_ids"] = [Command.set(products.ids)]
        if "base_product_id" in field_names:
            values["base_product_id"] = products[0].id
        if "new_template_name" in field_names:
            values["new_template_name"] = (
                self._get_common_product_template_name(products)
                or products[0].product_tmpl_id.name
                or _("Combined Products")
            )
        if "line_ids" in field_names:
            variant_names = self._get_default_variant_value_names(products)
            values["line_ids"] = [
                Command.create(
                    {
                        "product_id": product.id,
                        "variant_value_name": variant_names[product.id],
                    }
                )
                for product in products
            ]
        return values

    @api.onchange("product_ids")
    def _onchange_product_ids(self):
        for wizard in self:
            unique_products = self.env["product.product"].browse(
                list(dict.fromkeys(wizard.product_ids.ids))
            )
            variant_names = wizard._get_default_variant_value_names(unique_products)
            wizard.line_ids = [
                Command.clear(),
                *[
                    Command.create(
                        {
                            "product_id": product.id,
                            "variant_value_name": variant_names[product.id],
                        }
                    )
                    for product in unique_products
                ],
            ]
            if unique_products:
                wizard.new_template_name = (
                    wizard._get_common_product_template_name(unique_products)
                    or unique_products[:1].product_tmpl_id.name
                    or _("Combined Products")
                )
            else:
                wizard.new_template_name = False
            if wizard.base_product_id not in wizard.product_ids:
                wizard.base_product_id = wizard.product_ids[:1]

    @api.constrains("product_ids", "base_product_id")
    def _check_base_product(self):
        for wizard in self:
            if wizard.base_product_id and wizard.base_product_id not in wizard.product_ids:
                raise ValidationError(_("The base product must be one of the selected products."))

    @api.model
    def _get_product_name_for_variant_value(self, product):
        """Return the product name used when finding the common text."""
        value_name = (product.product_tmpl_id.name or "").strip()
        combination_name = (
            product.product_template_attribute_value_ids._get_combination_name()
        )
        if combination_name:
            value_name = _("%(template)s - %(combination)s",
                           template=value_name,
                           combination=combination_name)
        return " ".join(value_name.split())

    @api.model
    def _get_common_product_template_name(self, products):
        """Return the readable text common to all selected product names.

        The method uses the same leading/trailing comparison used for generated
        variant values. The unique middle portion is removed and the remaining
        common portions become the new template name.
        """
        products = products.exists()
        if not products:
            return ""

        source_names = [
            self._get_product_name_for_variant_value(product)
            for product in products
        ]
        if len(source_names) == 1:
            return source_names[0]

        token_matches = [
            list(re.finditer(r"[\w]+|[^\w\s]+", name))
            for name in source_names
        ]
        token_values = [
            [match.group(0).casefold() for match in matches]
            for matches in token_matches
        ]
        minimum_length = min((len(tokens) for tokens in token_values), default=0)

        common_prefix_length = 0
        while common_prefix_length < minimum_length:
            token = token_values[0][common_prefix_length]
            if any(
                tokens[common_prefix_length] != token
                for tokens in token_values[1:]
            ):
                break
            common_prefix_length += 1

        common_suffix_length = 0
        while common_suffix_length < minimum_length - common_prefix_length:
            token = token_values[0][-1 - common_suffix_length]
            if any(
                tokens[-1 - common_suffix_length] != token
                for tokens in token_values[1:]
            ):
                break
            common_suffix_length += 1

        first_matches = token_matches[0]
        common_tokens = [
            match.group(0)
            for match in first_matches[:common_prefix_length]
        ]
        if common_suffix_length:
            suffix_tokens = [
                match.group(0)
                for match in first_matches[-common_suffix_length:]
            ]
            # Avoid duplicated separators around the removed unique portion,
            # for example ``Product - Red - 1 L`` -> ``Product - 1 L``.
            if (
                common_tokens
                and suffix_tokens
                and not re.search(r"\w", common_tokens[-1])
                and common_tokens[-1] == suffix_tokens[0]
            ):
                suffix_tokens = suffix_tokens[1:]
            common_tokens.extend(suffix_tokens)

        common_name = self._format_name_tokens(common_tokens)
        if common_name:
            return common_name

        # Names such as Model500ML and Model1000ML differ inside a single token.
        # In that case derive a common character prefix and suffix.
        minimum_character_length = min(len(name) for name in source_names)
        common_character_prefix = 0
        while common_character_prefix < minimum_character_length:
            source_character = source_names[0][common_character_prefix]
            if source_character.isdigit() or any(
                name[common_character_prefix].casefold()
                != source_character.casefold()
                for name in source_names[1:]
            ):
                break
            common_character_prefix += 1

        common_character_suffix = 0
        while (
            common_character_suffix
            < minimum_character_length - common_character_prefix
        ):
            source_character = source_names[0][-1 - common_character_suffix]
            if source_character.isdigit() or any(
                name[-1 - common_character_suffix].casefold()
                != source_character.casefold()
                for name in source_names[1:]
            ):
                break
            common_character_suffix += 1

        # Ignore a one-character accidental match such as the trailing ``e``
        # in Apple and Orange.
        if common_character_prefix + common_character_suffix < 2:
            return ""

        prefix = source_names[0][:common_character_prefix]
        suffix = (
            source_names[0][-common_character_suffix:]
            if common_character_suffix
            else ""
        )
        strip_characters = " \t\r\n-–—_/\\|,:;.!?()[]{}'\""
        prefix = prefix.strip(strip_characters)
        suffix = suffix.strip(strip_characters)
        return " ".join(part for part in (prefix, suffix) if part).strip()

    @api.model
    def _format_name_tokens(self, tokens):
        """Convert name tokens back to a clean, readable product name."""
        if not tokens:
            return ""
        value = " ".join(tokens)
        value = re.sub(r"\s+", " ", value)
        value = re.sub(r"\s+([,.;:!?%)\]}}])", r"\1", value)
        value = re.sub(r"([(\[{{])\s+", r"\1", value)
        strip_characters = " \t\r\n-–—_/\\|,:;.!?()[]{}'\""
        return value.strip(strip_characters)

    @api.model
    def _get_default_variant_value_name(self, product):
        """Fallback descriptive value used when a unique name cannot be derived."""
        value_name = self._get_product_name_for_variant_value(product)
        if product.default_code:
            value_name = _("%(name)s [%(code)s]",
                           name=value_name,
                           code=product.default_code)
        return value_name or product.default_code or _("Variant")

    @api.model
    def _get_default_variant_value_names(self, products):
        """Strip common name portions and return one unique value per product.

        Common leading and trailing name tokens are removed. This handles names
        such as ``Product - Red - 1 L`` and ``Product - Blue - 1 L`` by
        returning ``Red`` and ``Blue``. The matching is case-insensitive and
        punctuation is treated as separate tokens, so ``Product-A`` and
        ``Product-B`` also become ``A`` and ``B``.
        """
        products = products.exists()
        if not products:
            return {}

        source_names = {
            product.id: self._get_product_name_for_variant_value(product)
            for product in products
        }
        token_matches = {
            product.id: list(re.finditer(r"[\w]+|[^\w\s]+", source_names[product.id]))
            for product in products
        }
        token_values = {
            product_id: [match.group(0).casefold() for match in matches]
            for product_id, matches in token_matches.items()
        }

        token_lists = list(token_values.values())
        minimum_length = min((len(tokens) for tokens in token_lists), default=0)

        common_prefix_length = 0
        while common_prefix_length < minimum_length:
            token = token_lists[0][common_prefix_length]
            if any(tokens[common_prefix_length] != token for tokens in token_lists[1:]):
                break
            common_prefix_length += 1

        common_suffix_length = 0
        while common_suffix_length < minimum_length - common_prefix_length:
            token = token_lists[0][-1 - common_suffix_length]
            if any(
                tokens[-1 - common_suffix_length] != token
                for tokens in token_lists[1:]
            ):
                break
            common_suffix_length += 1

        strip_characters = " \t\r\n-–—_/\\|,:;.!?()[]{}'\""
        names = {}
        for product in products:
            source_name = source_names[product.id]
            matches = token_matches[product.id]
            remaining_end = len(matches) - common_suffix_length
            if common_prefix_length < remaining_end:
                start = matches[common_prefix_length].start()
                end = matches[remaining_end - 1].end()
                candidate = source_name[start:end].strip(strip_characters)
            else:
                candidate = ""
            names[product.id] = candidate

        # When names differ inside a single token (for example Model500ML and
        # Model1000ML), token stripping cannot find the common text. In that
        # case, also remove a common character prefix and suffix.
        if all(
            names[product.id] == source_names[product.id]
            for product in products
        ):
            character_names = list(source_names.values())
            minimum_character_length = min(
                (len(name) for name in character_names),
                default=0,
            )
            common_character_prefix = 0
            while common_character_prefix < minimum_character_length:
                source_character = character_names[0][common_character_prefix]
                character = source_character.casefold()
                if source_character.isdigit() or any(
                    name[common_character_prefix].casefold() != character
                    for name in character_names[1:]
                ):
                    break
                common_character_prefix += 1

            common_character_suffix = 0
            while (
                common_character_suffix
                < minimum_character_length - common_character_prefix
            ):
                source_character = character_names[0][
                    -1 - common_character_suffix
                ]
                character = source_character.casefold()
                if source_character.isdigit() or any(
                    name[-1 - common_character_suffix].casefold() != character
                    for name in character_names[1:]
                ):
                    break
                common_character_suffix += 1

            if common_character_prefix or common_character_suffix:
                for product in products:
                    source_name = source_names[product.id]
                    end = (
                        len(source_name) - common_character_suffix
                        if common_character_suffix
                        else len(source_name)
                    )
                    names[product.id] = source_name[
                        common_character_prefix:end
                    ].strip(strip_characters)

        # The stripped portions may still leave empty or duplicate values when
        # names are identical. Prefer the internal reference in that situation,
        # then fall back to the original descriptive value and a numbered value.
        grouped_products = defaultdict(list)
        for product in products:
            grouped_products[(names[product.id] or "").casefold()].append(product)

        used_names = set()
        final_names = {}
        for position, product in enumerate(products, start=1):
            candidate = names[product.id]
            duplicate_candidate = len(
                grouped_products[(candidate or "").casefold()]
            ) > 1
            if not candidate or duplicate_candidate:
                if product.default_code:
                    candidate = product.default_code.strip()
                if not candidate or candidate.casefold() in used_names:
                    candidate = self._get_default_variant_value_name(product)
                if not candidate or candidate.casefold() in used_names:
                    candidate = _("Variant %(number)s", number=position)

            original_candidate = candidate
            suffix = 2
            while candidate.casefold() in used_names:
                candidate = _("%(name)s %(number)s",
                              name=original_candidate,
                              number=suffix)
                suffix += 1
            used_names.add(candidate.casefold())
            final_names[product.id] = candidate

        return final_names

    def _get_fields_requiring_same_value(self):
        """Template-level behavior that cannot safely differ between variants."""
        return [
            "detailed_type",
            "uom_id",
            "uom_po_id",
            "sale_ok",
            "purchase_ok",
            "taxes_id",
            "route_ids",
            "tracking",
            "invoice_policy",
            "purchase_method",
            "service_type",
            "service_tracking",
            "expense_policy",
        ]

    def _get_template_fields_to_copy(self):
        """Extension hook for additional standard or custom template fields."""
        return [
            "detailed_type",
            "categ_id",
            "uom_id",
            "uom_po_id",
            "sale_ok",
            "purchase_ok",
            "available_in_pos",
            "description",
            "description_sale",
            "description_purchase",
            "color",
            "sequence",
            "taxes_id",
            "supplier_taxes_id",
            "route_ids",
            "tracking",
            "invoice_policy",
            "purchase_method",
            "responsible_id",
            "service_type",
            "service_tracking",
            "expense_policy",
            "project_id",
            "project_template_id",
            "sale_line_warn",
            "sale_line_warn_msg",
            "purchase_line_warn",
            "purchase_line_warn_msg",
            "product_tag_ids",
            "optional_product_ids",
            "accessory_product_ids",
            "alternative_product_ids",
            "property_account_income_id",
            "property_account_expense_id",
        ]

    @api.model
    def _normalized_field_value(self, record, field_name):
        field = record._fields[field_name]
        value = record[field_name]
        if field.type == "many2one":
            return value.id or False
        if field.type in ("many2many", "one2many"):
            return tuple(sorted(value.ids))
        return value

    def _validate_products(self, products):
        if len(products) < 2:
            raise UserError(_("Select at least two product variants to combine."))

        if not (self.new_template_name or "").strip():
            raise UserError(_("Enter a name for the new product template."))

        if not (self.variant_attribute_name or "").strip():
            raise UserError(_("Enter the variant attribute before combining the products."))

        if self.base_product_id not in products:
            raise UserError(_("The base product must be one of the selected products."))

        templates = products.product_tmpl_id
        base_template = self.base_product_id.product_tmpl_id
        different_fields = []

        # Empty company means the product is shared. It is compatible with one
        # concrete company, but products assigned to two different companies
        # still cannot become variants of the same template.
        non_empty_company_ids = set(templates.mapped("company_id").ids)
        if len(non_empty_company_ids) > 1:
            different_fields.append(
                base_template._fields["company_id"].string
            )

        for field_name in self._get_fields_requiring_same_value():
            if field_name not in base_template._fields:
                continue
            base_value = self._normalized_field_value(base_template, field_name)
            if any(
                self._normalized_field_value(template, field_name) != base_value
                for template in templates
            ):
                different_fields.append(base_template._fields[field_name].string)

        if different_fields:
            raise UserError(
                _(
                    "The selected products have different template-level settings that "
                    "cannot vary by product variant. Make these fields identical first:\n- %(fields)s",
                    fields="\n- ".join(different_fields),
                )
            )

        selected_line_products = self.line_ids.mapped("product_id")
        if set(selected_line_products.ids) != set(products.ids):
            raise UserError(_("Each selected product must have exactly one variant value line."))
        if len(self.line_ids) != len(products):
            raise UserError(_("Each selected product must have exactly one variant value line."))

        names = []
        for line in self.line_ids:
            clean_name = (line.variant_value_name or "").strip()
            if not clean_name:
                raise UserError(_("Every product must have a non-empty variant value."))
            names.append(clean_name.casefold())
        if len(names) != len(set(names)):
            raise UserError(_("Variant value names must be unique within the new template."))

    def _prepare_new_template_vals(self, base_template, base_sale_price, products):
        values = {
            "name": self.new_template_name.strip(),
            "active": True,
            "list_price": base_sale_price,
        }
        for field_name in self._get_template_fields_to_copy():
            if field_name not in base_template._fields:
                continue
            field = base_template._fields[field_name]
            if field.compute and not field.inverse:
                continue
            value = base_template[field_name]
            if field.type == "many2one":
                values[field_name] = value.id or False
            elif field.type == "many2many":
                values[field_name] = [Command.set(value.ids)]
            elif field.type not in ("one2many", "binary"):
                values[field_name] = value

        source_templates = products.product_tmpl_id

        # A shared product (company_id=False) may be merged with products from
        # one company. In that case the resulting template belongs to that
        # concrete company. If all products are shared, it remains shared.
        target_companies = source_templates.mapped("company_id")
        values["company_id"] = target_companies.id if len(target_companies) == 1 else False

        # POS availability is template-level. Preserve availability whenever at
        # least one selected product was available in POS instead of silently
        # disabling the newly created template.
        if "available_in_pos" in base_template._fields:
            values["available_in_pos"] = any(
                source_templates.mapped("available_in_pos")
            )

        return values

    def _capture_vendor_pricelists(self, products):
        if not self.migrate_vendor_pricelists:
            return {}
        snapshots = {}
        SupplierInfo = self.env["product.supplierinfo"].with_context(active_test=False)
        for product in products:
            snapshots[product.id] = SupplierInfo.search(
                [
                    ("product_tmpl_id", "=", product.product_tmpl_id.id),
                    "|",
                    ("product_id", "=", False),
                    ("product_id", "=", product.id),
                ]
            )
        return snapshots

    def _restore_vendor_pricelists(self, products, new_template, snapshots):
        if not snapshots:
            return
        for product in products:
            for seller in snapshots.get(product.id, self.env["product.supplierinfo"]):
                if seller.product_id == product:
                    seller.write({"product_tmpl_id": new_template.id})
                elif not seller.product_id:
                    seller.copy(
                        {
                            "product_tmpl_id": new_template.id,
                            "product_id": product.id,
                        }
                    )

    def _archive_empty_source_templates(self, source_templates):
        if not self.archive_empty_templates:
            return self.env["product.template"]

        archived_templates = self.env["product.template"]
        Product = self.env["product.product"].with_context(active_test=False)
        for template in source_templates:
            if not Product.search_count([("product_tmpl_id", "=", template.id)]):
                template.write({"active": False})
                archived_templates |= template
        return archived_templates

    def _after_products_combined(self, products, new_template, source_templates):
        """Extension hook called after the products have been moved."""
        return None

    def action_combine(self):
        self.ensure_one()
        products = self.product_ids.with_context(active_test=False).exists()
        self._validate_products(products)

        source_templates = products.product_tmpl_id
        original_active_ids = set(products.filtered("active").ids)
        sale_prices = {product.id: product.lst_price for product in products}
        base_sale_price = (
            min(sale_prices.values())
            if self.preserve_sale_prices
            else self.base_product_id.product_tmpl_id.list_price
        )

        fallback_images = {}
        for product in products.with_context(bin_size=False):
            if not product.image_variant_1920 and product.product_tmpl_id.image_1920:
                fallback_images[product.id] = product.product_tmpl_id.image_1920

        vendor_snapshots = self._capture_vendor_pricelists(products)

        template_values = self._prepare_new_template_vals(
            self.base_product_id.product_tmpl_id,
            base_sale_price,
            products,
        )
        new_template = self.env["product.template"].with_context(
            create_product_product=False
        ).create(template_values)

        attribute = self.env["product.attribute"].create(
            {
                "name": self.variant_attribute_name.strip(),
                "create_variant": "always",
                "display_type": "radio",
            }
        )

        line_by_product = {line.product_id.id: line for line in self.line_ids}
        attribute_values = self.env["product.attribute.value"].create(
            [
                {
                    "name": line_by_product[product.id].variant_value_name.strip(),
                    "attribute_id": attribute.id,
                }
                for product in products
            ]
        )
        value_by_product = dict(zip(products.ids, attribute_values))

        attribute_line = self.env["product.template.attribute.line"].with_context(
            create_product_product=False
        ).create(
            {
                "product_tmpl_id": new_template.id,
                "attribute_id": attribute.id,
                "value_ids": [Command.set(attribute_values.ids)],
            }
        )

        ptav_values = []
        for product in products:
            extra_price = (
                sale_prices[product.id] - base_sale_price
                if self.preserve_sale_prices
                else 0.0
            )
            ptav_values.append(
                {
                    "product_attribute_value_id": value_by_product[product.id].id,
                    "attribute_line_id": attribute_line.id,
                    "price_extra": extra_price,
                }
            )
        template_attribute_values = self.env["product.template.attribute.value"].create(
            ptav_values
        )
        ptav_by_product = dict(zip(products.ids, template_attribute_values))

        # The active-only unique index on (template, combination) makes temporary
        # archiving the safest way to move several existing variants atomically.
        products.filtered("active").write({"active": False})
        for product in products:
            product.write(
                {
                    "product_tmpl_id": new_template.id,
                    "product_template_attribute_value_ids": [
                        Command.set([ptav_by_product[product.id].id])
                    ],
                }
            )
            if product.id in fallback_images:
                product.with_context(bin_size=False).write(
                    {"image_variant_1920": fallback_images[product.id]}
                )

        # Ensure the stored combination index is recomputed before the products
        # are reactivated and checked by the active-only unique SQL index.
        products.flush_recordset(["product_tmpl_id", "combination_indices"])

        products.filtered(lambda product: product.id in original_active_ids).write(
            {"active": True}
        )

        self._restore_vendor_pricelists(products, new_template, vendor_snapshots)
        self._archive_empty_source_templates(source_templates)
        self._after_products_combined(products, new_template, source_templates)

        new_template.invalidate_recordset()
        products.invalidate_recordset()

        return {
            "type": "ir.actions.act_window",
            "name": new_template.display_name,
            "res_model": "product.template",
            "view_mode": "form",
            "res_id": new_template.id,
            "target": "current",
        }


class ProductVariantCombineWizardLine(models.TransientModel):
    _name = "product.variant.combine.wizard.line"
    _description = "Product Variant Combination Line"
    _order = "id"

    wizard_id = fields.Many2one(
        comodel_name="product.variant.combine.wizard",
        required=True,
        ondelete="cascade",
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
        required=True,
        ondelete="cascade",
    )
    source_template_id = fields.Many2one(
        comodel_name="product.template",
        string="Source Template",
        related="product_id.product_tmpl_id",
        readonly=True,
    )
    internal_reference = fields.Char(
        string="Internal Reference",
        related="product_id.default_code",
        readonly=True,
    )
    current_sale_price = fields.Float(
        string="Current Sale Price",
        related="product_id.lst_price",
        readonly=True,
    )
    variant_value_name = fields.Char(
        string="New Variant Value",
        required=True,
    )
