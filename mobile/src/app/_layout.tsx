import {
  Newsreader_500Medium,
  Newsreader_600SemiBold,
} from '@expo-google-fonts/newsreader';
import {
  PlusJakartaSans_500Medium,
  PlusJakartaSans_600SemiBold,
  PlusJakartaSans_700Bold,
} from '@expo-google-fonts/plus-jakarta-sans';
import { useFonts } from 'expo-font';
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
function SplashController({ fontsReady }: { fontsReady: boolean }) {
  const { loading } = useSession();

  useEffect(() => {
    // Both, not either: revealing the app before the fonts land shows a frame
    // of system-font fallback and then reflows, which is worse than waiting.
    if (!loading && fontsReady) SplashScreen.hideAsync();
  }, [loading, fontsReady]);

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

  const [fontsLoaded, fontError] = useFonts({
    Newsreader_500Medium,
    Newsreader_600SemiBold,
    PlusJakartaSans_500Medium,
    PlusJakartaSans_600SemiBold,
    PlusJakartaSans_700Bold,
  });

  // A font that fails to load must not hold the app hostage — fall through to
  // the system face rather than showing a splash screen forever.
  const fontsReady = fontsLoaded || fontError !== null;

  return (
    <SessionProvider>
      <ThemeProvider value={colorScheme === 'dark' ? DarkTheme : DefaultTheme}>
        <SplashController fontsReady={fontsReady} />
        <AnimatedSplashOverlay />
        {fontsReady ? <RootNavigator /> : null}
      </ThemeProvider>
    </SessionProvider>
  );
}
