import { RamsarMapSection } from "@/components/home/ramsar-map-section";
import { RamsarOverview } from "@/components/home/ramsar-overview";
import { WetlandCarousel } from "@/components/home/wetland-carousel";
import { getCarouselSlides } from "@/lib/data/slides";

export default function Home() {
  return (
    <>
      <WetlandCarousel slides={getCarouselSlides()} />
      <RamsarOverview />
      <RamsarMapSection />
    </>
  );
}
