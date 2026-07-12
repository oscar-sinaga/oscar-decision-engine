class BreadcrumbState {
	entityLabel = $state<string | null>(null);
}

export const breadcrumbs = new BreadcrumbState();

export function setBreadcrumb(entityLabel: string | null): void {
	breadcrumbs.entityLabel = entityLabel;
}
