import { createAuthBridge, startLogin } from './auth-bridge.ts';
import type { UnlistenFn } from '@tauri-apps/api/event';

function ok(condition: boolean, message: string): void {
	if (!condition) throw new Error(`FAIL: ${message}`);
}

const calls: Array<{ kind: string; name: string; payload?: unknown }> = [];
const listeners = new Map<string, (event: { payload: unknown }) => void>();
const unlisten: UnlistenFn = () => {};
const bridge = createAuthBridge(
	async <T>(command: string, args?: Record<string, unknown>) => {
		calls.push({ kind: 'invoke', name: command, payload: args });
		return undefined as T;
	},
	async <T>(event: string, handler: (event: { payload: T }) => void) => {
		calls.push({ kind: 'listen', name: event });
		listeners.set(event, handler as (event: { payload: unknown }) => void);
		return unlisten;
	}
);

await bridge.loginWebview();
ok(calls[0]?.kind === 'invoke' && calls[0].name === 'login_webview', 'login invokes native command');

let receivedAuth: unknown;
let receivedError = '';
let completed = false;
let selectionRequired = false;
await bridge.onAuthChanged((account: { signedIn: boolean }) => (receivedAuth = account));
await bridge.onAccountSelectionRequired(() => (selectionRequired = true));
await bridge.onLoginError((message) => (receivedError = message));
await bridge.onLoginDone(() => (completed = true));
listeners.get('auth-changed')?.({ payload: { signedIn: true } });
listeners.get('account-selection-required')?.({ payload: undefined });
listeners.get('login-error')?.({ payload: 'Sign-in timed out. Please try again.' });
listeners.get('login-done')?.({ payload: undefined });
ok((receivedAuth as { signedIn: boolean }).signedIn, 'auth event payload reaches UI');
ok(selectionRequired, 'account-selection event reaches UI');
ok(receivedError.includes('timed out'), 'login error payload reaches UI');
ok(completed, 'login completion event reaches UI');

let recoverableError = '';
await startLogin(async () => {
	throw new Error('native bridge unavailable');
}, (message) => (recoverableError = message));
ok(recoverableError === 'Error: native bridge unavailable', 'invoke rejection becomes recoverable UI error');

console.log('ok');
