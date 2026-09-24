import os
import qrcode


def generate_qr_cards(students, output_folder):

    os.makedirs(output_folder, exist_ok=True)

    for candidate, name in students.items():

        qr = qrcode.make(candidate)

        filename = f"{candidate}_{name}.png"

        qr.save(
            os.path.join(
                output_folder,
                filename
            )
        )
