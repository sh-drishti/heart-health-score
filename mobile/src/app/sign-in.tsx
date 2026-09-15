import { useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  TextInput,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ApiError } from '@/api/client';
import { useSession } from '@/auth/ctx';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Radius, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

export default function SignIn() {
  const { signIn } = useSession();
  const theme = useTheme();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    if (!email.trim() || !password) return;

    setBusy(true);
    setError(null);

    try {
      await signIn(email, password);
      // No navigation here. Setting the session flips the guard in the root
      // layout, and the router follows — so this screen never has to know
      // where a given role belongs.
    } catch (e) {
      setError(
        e instanceof ApiError
          ? e.message
          : 'Something went wrong. Please try again.',
      );
    } finally {
      setBusy(false);
    }
  };

  const disabled = busy || !email.trim() || !password;

  return (
    <ThemedView style={styles.fill}>
      <SafeAreaView style={styles.fill}>
        <KeyboardAvoidingView
          style={styles.fill}
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
          <ScrollView
            contentContainerStyle={styles.scroll}
            keyboardShouldPersistTaps="handled">
            <ThemedView style={styles.form}>
              <ThemedText type="title">Heart Health Score</ThemedText>
              <ThemedText type="small" style={styles.subtitle}>
                Sign in to see your score and record a visit.
              </ThemedText>

              <ThemedText type="small" style={styles.label}>
                Email
              </ThemedText>
              <TextInput
                value={email}
                onChangeText={setEmail}
                placeholder="you@example.com"
                placeholderTextColor={theme.textSecondary}
                autoCapitalize="none"
                autoCorrect={false}
                autoComplete="email"
                keyboardType="email-address"
                inputMode="email"
                returnKeyType="next"
                editable={!busy}
                style={[
                  styles.input,
                  { color: theme.text, backgroundColor: theme.backgroundElement },
                ]}
              />

              <ThemedText type="small" style={styles.label}>
                Password
              </ThemedText>
              <TextInput
                value={password}
                onChangeText={setPassword}
                placeholder="••••••••"
                placeholderTextColor={theme.textSecondary}
                secureTextEntry
                autoCapitalize="none"
                autoComplete="current-password"
                returnKeyType="go"
                onSubmitEditing={submit}
                editable={!busy}
                style={[
                  styles.input,
                  { color: theme.text, backgroundColor: theme.backgroundElement },
                ]}
              />

              {error ? (
                <ThemedText type="small" themeColor="error" style={styles.error}>
                  {error}
                </ThemedText>
              ) : null}

              <Pressable
                onPress={submit}
                disabled={disabled}
                style={({ pressed }) => [
                  styles.button,
                  { backgroundColor: theme.primary, opacity: disabled ? 0.45 : pressed ? 0.85 : 1 },
                ]}>
                {busy ? (
                  <ActivityIndicator color="#FFFFFF" />
                ) : (
                  <ThemedText style={[styles.buttonLabel, { color: '#FFFFFF' }]}>
                    Sign in
                  </ThemedText>
                )}
              </Pressable>

              <ThemedText type="small" style={styles.footnote}>
                Accounts are issued by your clinic. There is no self sign-up here
                yet, and no way to reset a forgotten password from the app —
                ask whoever set your account up.
              </ThemedText>
            </ThemedView>
          </ScrollView>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1 },
  scroll: { flexGrow: 1, justifyContent: 'center', padding: Spacing.four },
  // Not MaxContentWidth (800) — that is right for reading, far too wide
  // for a two-field form on a tablet.
  form: { width: '100%', maxWidth: 420, alignSelf: 'center', gap: 8 },
  subtitle: { marginBottom: 24 },
  label: { marginTop: 12 },
  input: {
    borderRadius: Radius.md,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 16,
  },
  error: { marginTop: 12 },
  button: {
    marginTop: 24,
    borderRadius: Radius.md,
    paddingVertical: 14,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 48,
  },
  buttonLabel: { fontSize: 16 },
  footnote: { marginTop: 24, opacity: 0.7 },
});
