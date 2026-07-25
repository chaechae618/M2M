import { SignupForm } from "@/features/auth/components/SignupForm";

export default function SignupPage() {
  return (
    <main className="flex min-h-screen justify-center bg-white px-5 py-14 sm:px-8 lg:py-[clamp(72px,9.766vh,100px)]">
      <SignupForm />
    </main>
  );
}
