import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { Copy, Check as CheckIcon } from 'lucide-react';

// The local companion server (`myace serve`) is what actually reads this
// machine's filesystem — the browser has no filesystem access of its own.
// Shared by ImportPage.tsx (scanning) and SetupAudit.tsx (auditing) since
// both need the exact same "is it running, and if not, how do I start it"
// panel — see AGENTS.md rule 24.
export const COMPANION_URLS = ['http://localhost:8765', 'http://127.0.0.1:8765'];

interface CompanionHealth {
  status: string;
  server: string;
}

/**
 * Polls the companion server's /health across both candidate URLs and
 * reports whether it's reachable. Shared by ImportPage.tsx and
 * SetupAudit.tsx so the two pages can't quietly drift on retry/polling
 * behavior the way they had before this was extracted.
 */
export function useCompanionHealth(enabled: boolean = true): UseQueryResult<CompanionHealth> {
  return useQuery({
    queryKey: ['companion-health'],
    queryFn: async () => {
      for (const baseUrl of COMPANION_URLS) {
        try {
          const res = await fetch(`${baseUrl}/health`, {
            mode: 'cors',
            cache: 'no-cache',
            signal: AbortSignal.timeout(3000),
          });
          if (res.ok) {
            const data = (await res.json()) as CompanionHealth;
            console.info(`[myace] Companion detected at ${baseUrl}`, data);
            return data;
          }
        } catch (err) {
          console.debug(`[myace] Companion not found at ${baseUrl}:`, err);
        }
      }
      throw new Error('Companion unreachable at localhost:8765 or 127.0.0.1:8765');
    },
    enabled,
    retry: 3,
    retryDelay: 3000,
    refetchInterval: 5000,
    staleTime: 0,
  });
}

type Platform = 'linux-x86_64' | 'macos-x86_64' | 'macos-arm64' | 'windows-x86_64' | null;

function detectPlatform(): Platform {
  const p = navigator.platform.toLowerCase();
  const ua = navigator.userAgent.toLowerCase();
  if (p.includes('win')) return 'windows-x86_64';
  if (p.includes('mac')) {
    // Apple Silicon Macs report "MacARM"; Intel Macs report "MacIntel"
    return p.includes('arm') || ua.includes('arm') ? 'macos-arm64' : 'macos-x86_64';
  }
  if (p.includes('linux')) return 'linux-x86_64';
  return null;
}

const PLATFORM_INFO: Record<NonNullable<Platform>, { label: string; icon: string }> = {
  'linux-x86_64': { label: 'Linux (x86_64)', icon: '🐧' },
  'macos-x86_64': { label: 'macOS (Intel)', icon: '🍏' },
  'macos-arm64': { label: 'macOS (Apple Silicon)', icon: '🍎' },
  'windows-x86_64': { label: 'Windows (x86_64)', icon: '🪟' },
};

const GH_LATEST = 'https://github.com/niels-emmer/myace/releases/download/latest';

export function LocalCompanionSetup({
  sourcePath,
  collectionName,
}: {
  sourcePath: string;
  collectionName: string;
}) {
  const backendOrigin = window.location.origin;
  const detectedPlatform = detectPlatform();
  const bootstrapCommand = `export MYACE_SERVER=${backendOrigin}; curl -fsSL https://raw.githubusercontent.com/niels-emmer/myace/main/scripts/bootstrap-import.sh | bash`;
  const installCommand = 'pipx install "myace-cli[serve] @ git+https://github.com/niels-emmer/myace.git#subdirectory=cli"';
  const loginCommand = `myace login --server ${backendOrigin} --token <token-from-Settings>`;
  const serveCommand = 'myace serve';
  const oneShotCommand = `myace import --path "${sourcePath}" --name "${collectionName}" --push`;

  return (
    <div className="p-4 bg-muted rounded-lg space-y-4">
      <p className="text-sm text-foreground font-medium">
        Local companion server not detected
      </p>
      <p className="text-xs text-muted-foreground">
        This page needs the <code className="bg-background px-1 rounded">myace</code> CLI
        running on your machine to read local files. Download the binary for your platform:
      </p>

      {/* ── Download buttons ─────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {(Object.entries(PLATFORM_INFO) as [Platform, typeof PLATFORM_INFO['linux-x86_64']][]).map(
          ([platform, info]) => {
            const isDetected = platform === detectedPlatform;
            return (
              <a
                key={platform}
                href={`${GH_LATEST}/myace-${platform}${platform === 'windows-x86_64' ? '.exe' : ''}`}
                target="_blank"
                rel="noopener noreferrer"
                className={`flex flex-col items-center gap-1 p-3 rounded-lg border text-center text-xs transition-colors ${
                  isDetected
                    ? 'border-brand-500 bg-brand-500/10 text-foreground'
                    : 'border-border bg-background text-muted-foreground hover:border-brand-300 hover:text-foreground'
                }`}
              >
                <span className="text-lg">{info.icon}</span>
                <span className="font-medium">{info.label}</span>
                {isDetected && (
                  <span className="text-[10px] text-brand-600 font-semibold uppercase tracking-wide">
                    Detected
                  </span>
                )}
              </a>
            );
          },
        )}
      </div>

      <div className="text-xs text-muted-foreground space-y-1">
        <p>
          After downloading, open a terminal and run:
        </p>
        <CliLine
          text={
            detectedPlatform === 'windows-x86_64'
              ? `.\\myace-windows-x86_64.exe login`
              : `chmod +x ./myace-${detectedPlatform ?? 'linux-x86_64'} && ./myace-${detectedPlatform ?? 'linux-x86_64'} login`
          }
        />
        <CliLine text={serveCommand} />
      </div>

      {/* ── Bootstrap script alternative ─────────────────────── */}
      <details className="text-sm">
        <summary className="text-muted-foreground cursor-pointer hover:text-foreground">
          Or use the automated bootstrap script
        </summary>
        <div className="mt-3 space-y-3">
          <p className="text-xs text-muted-foreground">
            The bootstrap script checks for Python, sets up a virtual environment, and installs
            the CLI. It also tries to download the pre-built binary if available.
          </p>
          <CliLine text={bootstrapCommand} />
          <p className="text-xs text-muted-foreground">
            View the script on{' '}
            <a
              href="https://github.com/niels-emmer/myace/blob/main/scripts/bootstrap-import.sh"
              target="_blank"
              rel="noopener noreferrer"
              className="text-brand-600 hover:underline"
            >
              GitHub
            </a>{' '}
            or use the{' '}
            <a
              href="https://github.com/niels-emmer/myace/blob/main/scripts/bootstrap-import.ps1"
              target="_blank"
              rel="noopener noreferrer"
              className="text-brand-600 hover:underline"
            >
              PowerShell version
            </a>{' '}
            for Windows.
          </p>
        </div>
      </details>

      {/* ── Manual pip setup ─────────────────────────────────── */}
      <details className="text-sm">
        <summary className="text-muted-foreground cursor-pointer hover:text-foreground">
          Manual setup via pip
        </summary>
        <div className="mt-3 space-y-3">
          <p className="text-xs text-foreground">
            <Link to="/settings" className="text-brand-600 hover:underline">
              Create an API token
            </Link>{' '}
            if you haven't yet, then run:
          </p>
          <CliLine text={installCommand} />
          <CliLine text={loginCommand} />
          <CliLine text={serveCommand} />
          <p className="text-xs text-muted-foreground pt-1">
            Prefer a one-off import instead? Run this after{' '}
            <code className="bg-background px-1 rounded">myace login</code>:
          </p>
          <CliLine text={oneShotCommand} />
        </div>
      </details>
    </div>
  );
}

export function CliLine({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <div className="flex items-center gap-2 bg-foreground text-background p-2 rounded font-mono text-xs">
      <code className="flex-1 break-all">{text}</code>
      <button onClick={handleCopy} className="shrink-0 p-1 hover:bg-background/10 rounded transition-colors">
        {copied ? (
          <CheckIcon className="h-3.5 w-3.5 text-green-400" />
        ) : (
          <Copy className="h-3.5 w-3.5 text-background/70" />
        )}
      </button>
    </div>
  );
}
