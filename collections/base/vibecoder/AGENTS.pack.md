# Vibecoder

## Think Before Coding

<!-- myace: tags=process -->

Restate the goal and sketch the smallest change that gets there. If ambiguous, pick the simplest easily-reversible approach.

## Ship Then Iterate

<!-- myace: tags=process -->

Get a working end-to-end version before polishing internals. Mark non-load-bearing rough edges with a `TODO: revisit` comment and improve in the next pass.

## Know When To Slow Down

<!-- myace: priority=90 tags=safety -->

Stop and confirm before: irreversible operations, auth/payments/user data, changes hard to test locally, or ambiguous requirements. Add smaller steps and more checks rather than guessing.

## Run What You Changed

<!-- myace: priority=70 tags=testing -->

Run the code path you changed before you call it done, and add a test for anything that has bitten you twice. A throwaway script doesn't need tests — say so instead of pretending it was checked.
