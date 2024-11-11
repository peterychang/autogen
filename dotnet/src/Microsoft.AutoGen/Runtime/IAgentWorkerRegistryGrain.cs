// Copyright (c) Microsoft Corporation. All rights reserved.
// IAgentWorkerRegistryGrain.cs

using Microsoft.AutoGen.Abstractions;

namespace Microsoft.AutoGen.Runtime;

public interface IAgentWorkerRegistryGrain : IGrainWithIntegerKey
{
    ValueTask RegisterAgentType(string type, IWorkerGateway worker);
    ValueTask UnregisterAgentType(string type, IWorkerGateway worker);
    ValueTask AddWorker(IWorkerGateway worker);
    ValueTask RemoveWorker(IWorkerGateway worker);
    ValueTask<(IWorkerGateway? Gateway, bool NewPlacment)> GetOrPlaceAgent(AgentId agentId);
}
