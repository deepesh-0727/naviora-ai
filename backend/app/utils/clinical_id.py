import qrcode
import io
import base64
from typing import str

def generate_patient_qr(patient_id: int) -> str:
    """
    Generates a high-resolution QR code for clinical check-in.
    Returns a base64 encoded PNG string.
    """
    qr_data = f"NAVIORA-ID-{patient_id:08d}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Save to memory stream
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")

    return base64.b64encode(buffered.getvalue()).decode()
