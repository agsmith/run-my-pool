import { Stack } from "expo-router";
import { Text } from "react-native";
import { Screen } from "@/components/Screen";
import { Card, ui } from "@/components/NativeUI";

export default function TermsScreen() {
  return (
    <Screen>
      <Stack.Screen options={{ title: "Terms of Use" }} />
      <Text style={ui.title}>Terms of Use</Text>
      <Text style={ui.copy}>Last updated September 30, 2026</Text>
      <Card>
        <Text style={ui.heading}>Entertainment pools</Text>
        <Text style={ui.copy}>Run My Pool is an entertainment service for sports pools. The app does not accept wagers, entry fees, or payments, and does not distribute prizes.</Text>
      </Card>
      <Card>
        <Text style={ui.heading}>Forum rules</Text>
        <Text style={ui.copy}>There is zero tolerance for harassment, hate speech, threats, sexual or explicit content, scams, spam, or sharing another person’s private information. Do not post content that is abusive, illegal, or intended to harm another person.</Text>
        <Text style={ui.copy}>Automated filters reject objectionable messages before they are posted. You can also report a message or block a member from the Forum. Reporting hides the message immediately. Blocking removes that member’s messages from your feed immediately and sends the selected message to Run My Pool for review.</Text>
        <Text style={ui.copy}>Run My Pool reviews safety reports within 24 hours. We remove objectionable content and suspend or eject users who provide abusive or prohibited content.</Text>
      </Card>
      <Card>
        <Text style={ui.heading}>Your agreement</Text>
        <Text style={ui.copy}>By signing in, you agree to follow these Terms of Use and the Forum rules. You may contact support@runmypool.net with a safety concern, appeal, or privacy question.</Text>
      </Card>
    </Screen>
  );
}
