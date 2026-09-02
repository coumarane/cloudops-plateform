import { notFound } from "next/navigation";
import { PlaceholderPage } from "@/components/layout/PlaceholderPage";
import { isPlaceholderSection, PLACEHOLDER_SECTIONS } from "@/lib/navigation";

export function generateStaticParams() {
  return PLACEHOLDER_SECTIONS.map((section) => ({ section }));
}

export default async function SectionPage({
  params,
}: {
  params: Promise<{ section: string }>;
}) {
  const { section } = await params;
  if (!isPlaceholderSection(section)) {
    notFound();
  }
  return <PlaceholderPage section={section} />;
}
