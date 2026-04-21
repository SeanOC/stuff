import Link from "next/link";

export default function Home() {
  return (
    <main style={{ padding: "2rem", maxWidth: 800, margin: "0 auto" }}>
      <h1>stuff — parametric models</h1>
      <p>
        Phase 1 slice: live WASM preview of one model with form-driven
        params. Gallery + STL download land in later phases.
      </p>
      <ul>
        <li>
          <Link href="/models/cylinder-holder-46">
            Multiconnect cylinder holder, 46mm
          </Link>
        </li>
      </ul>
    </main>
  );
}
