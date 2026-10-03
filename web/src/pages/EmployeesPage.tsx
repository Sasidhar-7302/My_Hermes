import { useLayoutEffect } from "react";
import { usePageHeader } from "@/contexts/usePageHeader";

export default function EmployeesPage() {
  const { setEnd } = usePageHeader();

  useLayoutEffect(() => {
    setEnd(null);
    return () => {
      setEnd(null);
    };
  }, [setEnd]);

  return (
    <div
      className="flex min-h-0 w-full min-w-0 flex-1 flex-col"
      style={{ minHeight: "calc(100vh - 5.5rem)", height: "100%" }}
    >
      <iframe
        src="http://localhost:8000"
        className="min-h-0 w-full min-w-0 flex-1 border-0"
        style={{ width: "100%", height: "100%", minHeight: "calc(100vh - 5.5rem)" }}
        title="Hermes Multi-Agent Company Dashboard"
      />
    </div>
  );
}
