import { PageContainer } from "@/components/layout/page-container";
import { PageHeading, Lead } from "@/components/ui/typography";

export function PagePlaceholder({ title, description }: { title: string; description?: string }) {
  return (
    <PageContainer className="section-y">
      <PageHeading>{title}</PageHeading>
      {description ? <Lead className="mt-3">{description}</Lead> : null}
    </PageContainer>
  );
}
