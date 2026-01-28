import process from 'node:process';

import { Generator, getConfig } from '@tanstack/router-generator';

const run = async () => {
  const root = process.cwd();

  // Uses apps/ui/tsr.config.json by default. Fail fast if config is missing/invalid.
  const config = getConfig(undefined, root);

  const generator = new Generator({ config, root });
  await generator.run();
};

run().catch((error) => {
  console.error('[generate-routes] Failed to generate TanStack Router route tree.');
  console.error(error);
  process.exitCode = 1;
});

