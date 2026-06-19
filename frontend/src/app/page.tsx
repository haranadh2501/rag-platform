// Temporary scaffold redirect — M13 will replace this with the marketing landing page.
import { redirect } from 'next/navigation';

export default function RootPage() {
  redirect('/admin/documents');
}
