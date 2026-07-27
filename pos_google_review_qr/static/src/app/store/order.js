/** @odoo-module **/

import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

const QR_IMAGE_SIZE = 256;
const qrCodeCache = new WeakMap();

/**
 * Generate a self-contained PNG instead of using /report/barcode.
 *
 * The ZXing encoder is part of Odoo 17's standard PoS asset bundle. Embedding
 * the PNG avoids failed or delayed image requests during receipt preview and
 * browser/hardware printing.
 */
function generateQrCodeDataUrl(value) {
    try {
        const zxing = window.ZXing;
        if (!zxing?.QRCodeWriter || !zxing?.BarcodeFormat?.QR_CODE) {
            throw new Error("Odoo ZXing QR encoder is not available");
        }

        const matrix = new zxing.QRCodeWriter().encode(
            value,
            zxing.BarcodeFormat.QR_CODE,
            QR_IMAGE_SIZE,
            QR_IMAGE_SIZE,
            null
        );
        const width = matrix.getWidth();
        const height = matrix.getHeight();
        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;

        const context = canvas.getContext("2d");
        if (!context) {
            throw new Error("A canvas context could not be created");
        }

        const image = context.createImageData(width, height);
        const pixels = image.data;
        let offset = 0;
        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                const color = matrix.get(x, y) ? 0 : 255;
                pixels[offset++] = color;
                pixels[offset++] = color;
                pixels[offset++] = color;
                pixels[offset++] = 255;
            }
        }
        context.putImageData(image, 0, 0);
        return canvas.toDataURL("image/png");
    } catch (error) {
        console.error("Unable to generate the Google review QR code.", error);
        return false;
    }
}

function getCachedQrCode(config, reviewUrl) {
    let cached = qrCodeCache.get(config);
    if (cached?.url !== reviewUrl) {
        cached = {
            url: reviewUrl,
            dataUrl: generateQrCodeDataUrl(reviewUrl),
        };
        qrCodeCache.set(config, cached);
    }
    return cached.dataUrl;
}

patch(Order.prototype, {
    export_for_printing() {
        const receiptData = super.export_for_printing(...arguments);
        const config = this.pos?.config;
        const reviewUrl = config?.google_review_url?.trim();

        if (config?.google_review_qr_enabled && reviewUrl) {
            const qrCode = getCachedQrCode(config, reviewUrl);
            if (qrCode) {
                receiptData.google_review_qr_code = qrCode;
                receiptData.google_review_qr_title = config.google_review_qr_title || "";
                receiptData.google_review_qr_message =
                    config.google_review_qr_message || "";
            }
        }

        return receiptData;
    },
});
