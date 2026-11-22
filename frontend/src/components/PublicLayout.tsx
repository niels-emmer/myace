import { Link, Outlet } from 'react-router-dom';
import GithubIcon from './GithubIcon';

/**
 * Minimal shell for the public storefront routes (`/packs`, `/packs/:id`).
 * Signed-in visitors keep the app `Layout` (see `PackBrowseShell` in
 * `App.tsx`); anonymous visitors get this header/footer instead of a sidebar
 * full of links that would bounce them to the login page.
 */
export default function PublicLayout() {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
          <Link to="/welcome" className="flex items-center gap-2">
            <img src="/logo.png" alt="MyACE" className="h-8 w-8" />
            <span className="text-lg font-bold text-foreground">MyACE</span>
          </Link>
          <div className="flex items-center gap-2 sm:gap-4">
            <Link
              to="/packs"
              className="hidden text-sm text-muted-foreground transition-colors hover:text-foreground sm:block"
            >
              Browse packs
            </Link>
            <a
              href="https://github.com/niels-emmer/myace"
              target="_blank"
              rel="noopener noreferrer"
              className="hidden items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground sm:flex"
            >
              <GithubIcon className="h-4 w-4" />
              GitHub
            </a>
            <Link
              to="/login"
              className="px-3 py-1.5 text-sm font-medium text-foreground transition-colors hover:text-brand-600"
            >
              Log in
            </Link>
            <Link
              to="/login?mode=register"
              className="rounded-lg bg-brand-600 px-4 py-1.5 text-sm font-medium text-white transition-colors hover:bg-brand-700"
            >
              Sign up
            </Link>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <Outlet />
      </main>

      <footer className="border-t border-border py-8 text-center">
        <p className="text-sm text-muted-foreground">
          MyACE is free and self-hostable. Browse packs without an account; create one only
          when you want to build or publish.
        </p>
      </footer>
    </div>
  );
}
