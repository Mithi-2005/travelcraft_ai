import process from "node:process";
import { parseCLI, startVitest } from "vitest/node";

const { filter, options } = parseCLI(["vitest", ...process.argv.slice(2)]);
options.run = true;
options.watch = false;

const ctx = await startVitest("test", filter, options, undefined, {
  stdin: process.stdin,
  stdout: process.stdout,
  stderr: process.stderr,
});

const exitCode = process.exitCode ?? 0;

if (ctx && typeof ctx.close === "function") {
  await ctx.close();
}

setImmediate(() => {
  process.exit(exitCode);
});
