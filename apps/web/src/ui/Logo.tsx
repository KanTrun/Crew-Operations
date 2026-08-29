import Link from "next/link";

export function Logo({ href = "/" }: { href?: string }) {
  return (
    <Link
      href={href}
      className="font-black uppercase tracking-tighter text-[var(--nq-copper)] text-lg md:text-xl"
      aria-label="NHỊP QUÁN — về trang chủ"
    >
      NHỊP<span className="text-[var(--nq-fg)]"> QUÁN</span>
    </Link>
  );
}
