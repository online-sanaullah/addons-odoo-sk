# -*- coding: utf-8 -*-

from lxml import etree


def inject_product_tag_filters(env, arch, domain_field):
    """Inject enabled product.tag filters into a search view arch."""
    try:
        search_arch = etree.fromstring(arch.encode('utf-8'))
    except Exception:
        return arch

    if search_arch.tag != 'search':
        return arch

    tags = env['product.tag'].sudo().search(
        [('show_in_product_search_filter', '=', True)],
        order='name, id',
    )
    if not tags:
        return arch

    existing_names = set(search_arch.xpath(".//filter[@name]/@name"))

    children = list(search_arch)
    if children and children[-1].tag != 'separator':
        search_arch.append(etree.Element('separator'))
    elif not children:
        # No separator needed visually, but keeping one before dynamic filters is harmless.
        search_arch.append(etree.Element('separator'))

    for tag in tags:
        filter_name = 'ptsf_product_tag_%s' % tag.id
        if filter_name in existing_names:
            continue

        node = etree.Element('filter')
        tag_label = tag.name or tag.display_name or ('Tag %s' % tag.id)
        node.set('string', tag_label)
        node.set('name', filter_name)
        node.set('domain', repr([(domain_field, 'in', [tag.id])]))
        node.set('help', 'Show products tagged with %s' % tag_label)
        search_arch.append(node)

    return etree.tostring(search_arch, encoding='unicode')
