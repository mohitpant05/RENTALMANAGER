export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen">
      <div className="hidden lg:flex lg:w-1/2 items-center justify-center bg-primary/5 p-12">
        <div className="max-w-md text-center">
          <div className="mb-6 flex justify-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary text-primary-foreground text-2xl font-bold">
              RM
            </div>
          </div>
          <h1 className="text-3xl font-bold tracking-tight">RentManager</h1>
          <p className="mt-3 text-muted-foreground text-lg">
            Multi-tenant rental management platform
          </p>
        </div>
      </div>
      <div className="flex w-full lg:w-1/2 items-center justify-center p-4">
        {children}
      </div>
    </div>
  );
}
