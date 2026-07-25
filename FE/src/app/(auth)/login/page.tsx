import { LoginForm } from "@/features/auth/components/LoginForm";
import { AuthBrandPanel } from "@/widgets/auth-brand-panel/AuthBrandPanel";

export default function LoginPage() {
  return (
    <main className="min-h-screen bg-white">
      <div className="flex min-h-screen w-full flex-col lg:flex-row">
        <div className="flex w-full justify-center p-3 lg:h-screen lg:w-1/2 lg:justify-end">
          <AuthBrandPanel />
        </div>
        <section className="flex flex-1 items-center justify-center px-5 py-10 lg:h-screen lg:w-1/2 lg:px-8 lg:py-[clamp(96px,17.676vh,181px)]">
          <LoginForm />
        </section>
      </div>
    </main>
  );
}
