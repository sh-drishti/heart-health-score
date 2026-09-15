/**
 * Everything behind a signed-in session.
 *
 * Reached only when the guard in the root layout passes, so no screen inside
 * needs its own auth check.
 */

import AppTabs from '@/components/app-tabs';

export default function AppLayout() {
  return <AppTabs />;
}
