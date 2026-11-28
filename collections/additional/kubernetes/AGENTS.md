# Kubernetes Engineer

Kubernetes workload and cluster-configuration conventions. This collection layers on a base collection
(DevOps Engineer or Software Engineer) and, for infrastructure work, on `iac-expert`; it adds the
Kubernetes layer: workload hygiene, pod security, RBAC, network policy and safe rollouts. It does not
cover a specific cloud's managed offering; combine it with the matching cloud collection for that.
Without those packs, still require explicit human approval before any apply to a shared cluster.

## Kubernetes Confirm The Target Before You Change It

<!-- myace: priority=90 tags=kubernetes,safety -->

Before any `kubectl apply`, `delete`, `scale`, `rollout`, `drain` or `helm upgrade`, state the cluster context and namespace you are acting on and confirm it is the intended one. Default to read-only commands and `--dry-run=server` plus `kubectl diff` first. Never delete a namespace, PersistentVolumeClaim, CRD or node pool, or apply to a production context, without explicit human approval of that exact action.

## Kubernetes Pods Run Least-Privilege

<!-- myace: priority=90 tags=kubernetes,security -->

Every workload sets a `securityContext`: `runAsNonRoot: true`, `allowPrivilegeEscalation: false`, `readOnlyRootFilesystem: true` where the app allows it, all capabilities dropped (add back only what is needed) and a `seccompProfile` of `RuntimeDefault`. No `privileged`, `hostNetwork`, `hostPID` or `hostPath` mounts without a documented exception. Enforce a Pod Security Admission level (target `restricted`) per namespace. See the `kubernetes-security-hardening` skill.

## Kubernetes Workloads Declare Resources And Health

<!-- myace: priority=70 tags=kubernetes,reliability -->

Every container sets CPU and memory requests (and a memory limit), plus readiness, liveness and, for slow starts, startup probes that check the app and not just the port. Use a PodDisruptionBudget and multiple replicas for anything that must stay up, spread across failure domains, and handle SIGTERM within the termination grace period. See the `kubernetes-workload-checklist` skill.

## Kubernetes Secrets And Images Are Controlled

<!-- myace: priority=90 tags=kubernetes,security,supply-chain -->

Never commit a Secret manifest with real values; source secrets from an external secret store or a sealed/encrypted mechanism, and mount them rather than baking them into images or environment lists that get logged. Reference images by immutable tag or digest from a trusted registry, never `latest`, and scan them in CI. Service accounts use a dedicated identity with automounted tokens disabled unless the pod calls the API.

## Kubernetes Network And Access Are Default-Deny

<!-- myace: priority=90 tags=kubernetes,security -->

Start every namespace with a default-deny NetworkPolicy and open only the flows needed (and confirm the cluster's CNI enforces NetworkPolicy). RBAC grants namespaced Roles to specific subjects with the narrowest verbs and resources; avoid wildcards and `cluster-admin`, and never bind it to a workload service account.

## Kubernetes Rollouts Are Reversible

<!-- myace: priority=70 tags=kubernetes,release -->

Ship changes through manifests in version control (Helm, Kustomize or plain YAML), not by hand-editing live objects. Use rolling updates with sensible `maxUnavailable`/`maxSurge`, wait for readiness, know the rollback command before you apply, and watch the rollout until it completes. Treat CRD, storage and API-version changes as separately approved migrations. See the `kubernetes-safe-rollouts` skill.
