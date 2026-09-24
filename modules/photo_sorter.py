import os
import shutil
import cv2

from pyzbar.pyzbar import decode


def sort_photos(source_folders,
                output_folder,
                students):

    sorted_count = 0
    failed_count = 0

    manual_review = os.path.join(
        output_folder,
        "Manual_Review"
    )

    os.makedirs(
        manual_review,
        exist_ok=True
    )

    for folder in source_folders:

        for file in os.listdir(folder):

            if not file.lower().endswith(
                    (".jpg", ".jpeg", ".png")):
                continue

            filepath = os.path.join(folder, file)

            image = cv2.imread(filepath)

            if image is None:
                continue

            decoded = decode(image)

            if decoded:

                candidate = decoded[0].data.decode()

                if candidate in students:

                    destination = os.path.join(
                        output_folder,
                        f"{candidate}_{students[candidate]}"
                    )

                    os.makedirs(
                        destination,
                        exist_ok=True
                    )

                    shutil.copy(
                        filepath,
                        os.path.join(
                            destination,
                            file
                        )
                    )

                    sorted_count += 1

                else:

                    shutil.copy(
                        filepath,
                        manual_review
                    )

                    failed_count += 1

            else:

                shutil.copy(
                    filepath,
                    manual_review
                )

                failed_count += 1

    return sorted_count, failed_count
