import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 p-6 text-center">
      <p className="text-sm font-semibold uppercase tracking-widest muted">404</p>
      <h1 className="text-xl font-semibold">This page does not exist</h1>
      <Link href="/" className="text-sm text-brand-600 underline">
        Back to the dashboard
      </Link>
    </div>
  );
}
