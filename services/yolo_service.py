from io import BytesIO

import numpy as np
from PIL import Image
from ultralytics import YOLO

model = YOLO("yolov8n.pt")


def detect_objects(image: Image.Image) -> tuple[bytes, list[dict]]:
    np_image = np.array(image.convert("RGB"))
    results = model.predict(source=np_image, verbose=False)

    if not results:
        buffer = BytesIO()
        image.save(buffer, format="JPEG")
        return buffer.getvalue(), []

    result = results[0]
    objects: list[dict] = []

    for box in result.boxes:
        cls_id = int(box.cls.item())
        confidence = float(box.conf.item())
        label = result.names.get(cls_id, str(cls_id))
        objects.append({"label": label, "confidence": round(confidence, 4)})

    plotted = result.plot()
    annotated = Image.fromarray(plotted[:, :, ::-1])

    output = BytesIO()
    annotated.save(output, format="JPEG", quality=95)
    return output.getvalue(), objects
