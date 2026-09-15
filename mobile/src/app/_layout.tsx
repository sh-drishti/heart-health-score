import { DarkTheme, DefaultTheme, Stack, ThemeProvider } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { useEffect } from 'react';
import { useColorScheme } from 'react-native';

import { SessionProvider, useSession } from '@/auth/ctx';
import { AnimatedSplashOverlay } from '@/components/animated-icon';

SplashScreen.preventAutoHideAsync();

/**
 * Holds the splash screen until the stored refresh token has been checked.
 *
 * Without this the app renders the sign-in screen for a moment and then jumps
 * to the dashboard, which reads as a bug to anyone who was already signed in.
 */
function SplashController() {
  const { loading } = useSession();

  useEffect(() => {
    if (!loading) SplashScreen.hideAsync();
  }, [loading]);

  return null;
}

function RootNavigator() {
  const { user } = useSession();

  // Stack.Protected keeps every route defined and redirects at runtime, rather
  // than conditionally mounting navigators — which is what makes a deep link
  // arriving before the session is restored land in the right place.
  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Protected guard={!!user}>
        <Stack.Screen name="(app)" />
      </Stack.Protected>

      <Stack.Protected guard={!user}>
        <Stack.Screen name="sign-in" />
      </Stack.Protected>
    </Stack>
  );
}

export default function RootLayout() {
  const colorScheme = useColorScheme();

  return (
    <SessionProvider>
      <ThemeProvider value={colorScheme === 'dark' ? DarkTheme : DefaultTheme}>
        <SplashController />
        <AnimatedSplashOverlay />
        <RootNavigator />
      </ThemeProvider>
    </SessionProvider>
  );
}
