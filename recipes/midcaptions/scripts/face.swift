// Face boxes with the Mac's built-in Vision (free, offline). Used to sit captions below the face.
// usage: face IMAGE...   prints one line per image: "top bottom" of the biggest face (0-1 from the top), or "none"
import Vision
import Foundation

for path in CommandLine.arguments.dropFirst() {
    let req = VNDetectFaceRectanglesRequest()
    let handler = VNImageRequestHandler(url: URL(fileURLWithPath: path))
    if (try? handler.perform([req])) != nil, let faces = req.results, !faces.isEmpty {
        let b = faces.max(by: { $0.boundingBox.width * $0.boundingBox.height < $1.boundingBox.width * $1.boundingBox.height })!.boundingBox
        print(String(format: "%.4f %.4f", 1 - b.maxY, 1 - b.minY))
    } else {
        print("none")
    }
}
