import { buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function Home() {
  return (
    <main className="flex flex-1 items-center justify-center p-6">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Hello, world 👋</CardTitle>
          <CardDescription>Platanus Hack 26 · Team 6</CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Next.js + shadcn/ui, running on Cloudflare Workers.
        </CardContent>
        <CardFooter>
          <a
            href="https://github.com/platanus-hack/platanus-hack-26-cl-team-6"
            target="_blank"
            rel="noopener noreferrer"
            className={buttonVariants()}
          >
            View on GitHub
          </a>
        </CardFooter>
      </Card>
    </main>
  );
}
