import { Stack } from 'expo-router';
import { Text, View } from 'react-native';
import { Screen } from '@/components/Screen';
import { ui } from '@/components/NativeUI';
import policy from '@/content/privacyPolicy.json';

export default function PrivacyScreen() {
  return <Screen>
    <Stack.Screen options={{ title: 'Privacy Policy' }} />
    <Text accessibilityRole="header" style={ui.heading}>{policy.title}</Text>
    <Text style={ui.copy}>Last updated: {policy.updated}</Text>
    <Text style={ui.copy}>{policy.intro}</Text>
    {policy.sections.map(section => <View key={section.title} style={{ gap: 12, marginTop: 16 }}>
      <Text accessibilityRole="header" style={ui.heading}>{section.title}</Text>
      {section.paragraphs.map(paragraph => <Text selectable key={paragraph} style={ui.copy}>{paragraph}</Text>)}
    </View>)}
  </Screen>;
}
