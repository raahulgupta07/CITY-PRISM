import { describe, expect, it } from 'vitest';
import { parseSse } from './sse';

describe('parseSse', () => {
	it('reads whole events and keeps the rest', () => {
		const { events, rest } = parseSse(
			'event: text\ndata: {"text":"A"}\n\nevent: text\ndata: {"text":"B"}\n\nevent: do'
		);
		expect(events).toEqual([
			{ event: 'text', data: '{"text":"A"}' },
			{ event: 'text', data: '{"text":"B"}' }
		]);
		expect(rest).toBe('event: do');
	});

	it('joins pieces split across reads', () => {
		const first = parseSse('event: done\nda');
		expect(first.events).toEqual([]);
		const second = parseSse(first.rest + 'ta: {}\n\n');
		expect(second.events).toEqual([{ event: 'done', data: '{}' }]);
		expect(second.rest).toBe('');
	});

	it('accepts CRLF line ends and skips comments', () => {
		const { events } = parseSse(
			': keep-alive\r\n\r\nevent: error\r\ndata: {"message":"x"}\r\n\r\n'
		);
		expect(events).toEqual([{ event: 'error', data: '{"message":"x"}' }]);
	});
});
