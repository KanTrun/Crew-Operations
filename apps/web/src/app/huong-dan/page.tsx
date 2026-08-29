import type { Metadata } from "next";
import MapGuide from "./MapGuide";

export const metadata: Metadata = {
  title: "Hướng dẫn · Bản đồ NHỊP QUÁN",
  description:
    "Bản đồ tương tác: bốn phòng vận hành, luồng một ngày quán, liên kết giữa các trang.",
};

export default function HuongDanPage() {
  return (
    <main id="nq-content" className="nq-map-root">
      <MapGuide />
    </main>
  );
}
