// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

var app = await Microsoft.AutoGen.Runtime.Host.StartAsync(local: false);
await app.WaitForShutdownAsync();
