export function formatRelativeTime(value: string, now = Date.now()): string {
	const date = new Date(value);
	if (Number.isNaN(date.getTime())) return value;
	const diff = Math.max(0, now - date.getTime());
	const minute = 60_000,
		hour = 60 * minute,
		day = 24 * hour;
	if (diff < minute) return 'just now';
	if (diff < hour) return `${Math.floor(diff / minute)}m ago`;
	if (diff < day) return `${Math.floor(diff / hour)}h ago`;
	if (diff < 7 * day) return `${Math.floor(diff / day)}d ago`;
	return new Intl.DateTimeFormat('en', {
		month: 'short',
		day: 'numeric',
		hour: '2-digit',
		minute: '2-digit',
		hour12: false
	}).format(date);
}
