import { useEffect } from 'react';
import { useRouter } from 'next/router';

export default function Register() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/create-account');
  }, [router]);

  return (
    <main>
      <p>Taking you to account creation…</p>
    </main>
  );
}
