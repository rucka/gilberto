import { redirect } from 'next/navigation'

// Landing page arrives with epic #29 (brand identity); until then the root serves the docs.
export default function Home() {
  redirect('/docs')
}
