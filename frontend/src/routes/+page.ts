import { appPath } from '$lib/app-path';
import { redirect } from '@sveltejs/kit';

export function load(): never {
	redirect(307, appPath('/dashboard'));
}
