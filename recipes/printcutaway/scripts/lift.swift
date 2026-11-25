// Cut-out masks using the Mac's built-in subject lifting (Vision, macOS 14+). Free and offline.
// usage: lift FRAMES_DIR MASKS_DIR [x y]
//   x y (0-1, from top-left): keep only the subject under this point. Without it: all subjects.
// Writes one greyscale PNG mask per frame, same name, white = keep.
import Vision
import CoreImage
import Foundation

let args = CommandLine.arguments
guard args.count >= 3 else { print("usage: lift FRAMES_DIR MASKS_DIR [x y]"); exit(2) }
let inDir = URL(fileURLWithPath: args[1]), outDir = URL(fileURLWithPath: args[2])
var point: CGPoint? = nil
if args.count >= 5, let x = Double(args[3]), let y = Double(args[4]) { point = CGPoint(x: x, y: y) }
try? FileManager.default.createDirectory(at: outDir, withIntermediateDirectories: true)
let files = try FileManager.default.contentsOfDirectory(atPath: inDir.path)
    .filter { $0.hasSuffix(".jpg") || $0.hasSuffix(".png") }.sorted()
let ctx = CIContext()
let gray = CGColorSpaceCreateDeviceGray()
var lastLabel: Int? = nil

func labelAt(_ buf: CVPixelBuffer, _ p: CGPoint) -> Int {
    CVPixelBufferLockBaseAddress(buf, .readOnly); defer { CVPixelBufferUnlockBaseAddress(buf, .readOnly) }
    let w = CVPixelBufferGetWidth(buf), h = CVPixelBufferGetHeight(buf)
    let row = CVPixelBufferGetBytesPerRow(buf)
    guard let base = CVPixelBufferGetBaseAddress(buf) else { return 0 }
    // look in a small neighbourhood, most common non-zero label wins
    var counts = [Int: Int]()
    let cx = Int(p.x * Double(w)), cy = Int(p.y * Double(h)), r = max(2, w / 40)
    for yy in max(0, cy - r)..<min(h, cy + r) {
        for xx in max(0, cx - r)..<min(w, cx + r) {
            let v = Int(base.load(fromByteOffset: yy * row + xx, as: UInt8.self))
            if v > 0 { counts[v, default: 0] += 1 }
        }
    }
    return counts.max(by: { $0.value < $1.value })?.key ?? 0
}

var done = 0, empty = 0
for f in files {
    let url = inDir.appendingPathComponent(f)
    let handler = VNImageRequestHandler(url: url)
    let req = VNGenerateForegroundInstanceMaskRequest()
    let outURL = outDir.appendingPathComponent((f as NSString).deletingPathExtension + ".png")
    var maskImage: CIImage? = nil
    if (try? handler.perform([req])) != nil, let r = req.results?.first, !r.allInstances.isEmpty {
        var chosen = r.allInstances
        if let p = point {
            let l = labelAt(r.instanceMask, p)
            if l > 0 { chosen = IndexSet(integer: l); lastLabel = l }
            else if let k = lastLabel, r.allInstances.contains(k) { chosen = IndexSet(integer: k) }
        }
        if let buf = try? r.generateScaledMaskForImage(forInstances: chosen, from: handler) {
            maskImage = CIImage(cvPixelBuffer: buf)
        }
    }
    if maskImage == nil {  // nothing found: fully transparent frame
        empty += 1
        let src = CIImage(contentsOf: url)!
        maskImage = CIImage(color: .black).cropped(to: src.extent)
    }
    try ctx.writePNGRepresentation(of: maskImage!, to: outURL, format: .L8, colorSpace: gray)
    done += 1
}
print("masks: \(done) frames, \(empty) with nothing found")
