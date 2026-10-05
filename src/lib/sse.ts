// Read server-sent events from a POST response (EventSource only does GET).

export interface SseEvent {
	event: string;
	data: string;
}

/** Split a growing buffer into whole events; return them and the unfinished rest. */
export function parseSse(buffer: string): { events: SseEvent[]; rest: string } {
	const blocks = buffer.replace(/\r\n/g, '\n').split('\n\n');
	const rest = blocks.pop() ?? '';
	const events: SseEvent[] = [];
	for (const block of blocks) {
		let event = 'message';
		const data: string[] = [];
		for (const line of block.split('\n')) {
			if (line.startsWith('event:')) event = line.slice(6).trim();
			else if (line.startsWith('data:')) data.push(line.slice(5).trimStart());
		}
		if (data.length) events.push({ event, data: data.join('\n') });
	}
	return { events, rest };
}

/**
 * Stream the AI portfolio summary from our server. Calls onText for each piece.
 * Resolves when the reply is complete; throws with a friendly message on error.
 */
export async function streamSummary(
	onText: (text: string) => void,
	signal: AbortSignal
): Promise<void> {
	const res = await fetch('/api/portfolio/summary', {
		method: 'POST',
		credentials: 'same-origin',
		signal
	});
	if (!res.ok || !res.body) {
		let message = 'Something went wrong. Please try again.';
		try {
			const body = await res.json();
			if (typeof body?.detail === 'string') message = body.detail;
		} catch {
			// keep the default message
		}
		throw new Error(message);
	}
	const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
	let buffer = '';
	for (;;) {
		const { value, done } = await reader.read();
		if (done) break;
		const parsed = parseSse(buffer + value);
		buffer = parsed.rest;
		for (const e of parsed.events) {
			const data = JSON.parse(e.data);
			if (e.event === 'text') onText(data.text);
			else if (e.event === 'error') throw new Error(data.message);
			else if (e.event === 'done') return;
		}
	}
	throw new Error('The summary stopped before it was finished. Please try again.');
}
