package main

import (
    "os"

    "gdu/internal/errors"
    "gdu/internal/pack"
)

func main() {
    code := run(os.Args[1:])
    os.Exit(code)
}

func run(args []string) int {
    if len(args) < 2 || args[0] != "pack" {
        errors.ExitJSON(errors.CliError{
            Code:    errors.InvalidArgs,
            Type:    "invalid_arguments",
            Message: "Usage: gdu pack <init|add|validate|digest|install> [flags]",
        })
        return int(errors.InvalidArgs)
    }

    sub := args[1]
    rest := args[2:]

    switch sub {
    case "validate":
        return pack.CmdValidate(rest)
    case "digest":
        return pack.CmdDigest(rest)
    case "init":
        return pack.CmdInit(rest)
    case "add":
        return pack.CmdAdd(rest)
    case "install":
        return pack.CmdInstall(rest)
    default:
        errors.ExitJSON(errors.CliError{
            Code:    errors.InvalidArgs,
            Type:    "invalid_arguments",
            Message: "Unknown subcommand: " + sub,
        })
        return int(errors.InvalidArgs)
    }
}
