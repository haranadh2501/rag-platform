"""Generate a deterministic Kubernetes troubleshooting evaluation dataset."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DEFAULT_DATASET = ROOT / "kubernetes_dataset.jsonl"
DEFAULT_SOURCE_DIR = ROOT / "sample-data" / "kubernetes_troubleshooting"


SOURCE_DOCUMENTS = {
    "cluster_debugging_runbook.txt": """Kubernetes Cluster Debugging Runbook

Section: Knowledge base source strategy
The Kubernetes troubleshooting knowledge base should prioritize the official Kubernetes debugging tasks, API reference, and kubectl command reference before community blogs, practical problem repositories, Kubernetes failure stories, and post-mortems. Managed service notes for EKS, GKE, and AKS should be layered after the core Kubernetes material.

Section: Initial triage packet
Every Kubernetes incident ticket should include the namespace, workload name and kind, affected node, image tag, recent deployment time, exact user-visible symptom, kubectl get output, kubectl describe output, relevant events, pod logs, and any recent configuration or secret changes. Secrets, tokens, and customer payloads must be redacted.

Section: Pending pods
When a pod remains Pending, inspect kubectl describe pod events first. Common causes are insufficient CPU or memory, unsatisfied node selectors or affinity, taints without tolerations, missing persistent volumes, and image pull secrets that are referenced but not present.

Section: CrashLoopBackOff
For CrashLoopBackOff, compare the current container logs with kubectl logs --previous. Check the exit code, command arguments, environment variables, mounted configuration, liveness probe behavior, and whether the process exits before the readiness gate can succeed.

Section: ImagePullBackOff
ImagePullBackOff usually means the kubelet cannot fetch the image. Validate the image name and tag, registry reachability, imagePullSecrets, service account permissions, and whether the registry is throttling or returning authentication failures.

Section: CreateContainerConfigError
CreateContainerConfigError commonly indicates that the pod spec references a missing ConfigMap, missing Secret, invalid key, or malformed environment variable source. Describe the pod and compare referenced names and keys with the objects in the same namespace.

Section: Node pressure and evictions
Node pressure evictions are driven by kubelet thresholds for memory, disk, PID, or ephemeral storage pressure. Inspect node conditions, eviction events, container ephemeral-storage usage, log growth, and whether requests and limits reflect actual workload behavior.

Section: Control plane health
Control-plane troubleshooting starts with kube-apiserver reachability, etcd health, scheduler and controller-manager status, certificate validity, and admission webhook latency. Avoid restarting multiple control-plane components at once unless an approved recovery runbook requires it.
""",
    "workload_network_storage_guide.txt": """Kubernetes Workload, Network, and Storage Guide

Section: Service has no endpoints
If a Service has no endpoints, compare the Service selector with pod labels and confirm matching pods are Ready. A typo in app labels, readiness probe failures, or selecting pods in the wrong namespace can leave the Service without usable backends.

Section: DNS resolution failure
For DNS failures, verify CoreDNS pods are Running and Ready, inspect CoreDNS logs, test resolution from a temporary debug pod, confirm the Service name and namespace, and check NetworkPolicies that could block traffic to kube-dns.

Section: NetworkPolicy isolation
NetworkPolicy is namespace scoped and becomes restrictive for selected pods once ingress or egress policies apply. Debug by checking pod labels, namespace labels, policy podSelector, policyTypes, ports, and whether the CNI plugin enforces NetworkPolicy.

Section: Ingress routing
Ingress failures should be split between DNS, load balancer, ingress controller, TLS secret, class annotation or ingressClassName, backend Service mapping, and pod readiness. Controller logs usually reveal whether the route was accepted or rejected.

Section: PersistentVolumeClaim Pending
A PersistentVolumeClaim remains Pending when no matching PersistentVolume exists or dynamic provisioning cannot satisfy the request. Check storageClassName, access modes, requested size, provisioner events, quota, and cloud-provider volume limits.

Section: Volume attach or detach failure
Volume attach and detach failures often involve stale node attachments, zone mismatch, cloud API throttling, CSI driver errors, or a previous pod still terminating. Confirm the pod node, volume zone, VolumeAttachment objects, CSI controller logs, and cloud-provider events.

Section: Autoscaling mismatch
HorizontalPodAutoscaler decisions depend on metrics availability, target utilization, resource requests, and stabilization windows. If replicas do not change, check metrics-server health, HPA conditions, pod resource requests, and whether maxReplicas has already been reached.

Section: Safe production debugging
Use kubectl debug or ephemeral containers for live inspection when possible. Avoid editing live Deployments without recording the change, avoid deleting PersistentVolumeClaims during diagnosis, and avoid collecting full environment dumps that may contain secrets.
""",
    "managed_kubernetes_failure_notes.txt": """Managed Kubernetes Failure Notes

Section: EKS networking faults
On EKS, pod networking failures often trace to AWS VPC CNI IP exhaustion, subnet address shortage, security group rules, route table drift, or IAM permissions for the CNI daemonset. Check aws-node logs and available subnet IP addresses before recreating nodes.

Section: EKS IAM authentication
EKS authentication failures can come from aws-auth ConfigMap drift, IAM role mapping mistakes, expired client credentials, or API server authentication webhook latency. Verify the caller identity and the aws-auth role or user mapping before changing RBAC.

Section: GKE Autopilot scheduling limits
On GKE Autopilot, scheduling can fail when requested resources, privileged settings, hostPath mounts, or unsupported security contexts violate Autopilot constraints. Review the admission error and adjust the workload rather than assuming node capacity is missing.

Section: GKE logging agent pressure
GKE logging agent anomalies can amplify node disk pressure when log volume spikes. Inspect container log growth, node filesystem usage, logging agent status, and whether noisy workloads need log sampling or rate reduction.

Section: AKS Azure CNI routing
On AKS with Azure CNI, pod connectivity issues may stem from subnet IP exhaustion, network security group rules, user-defined routes, or route propagation delays. Compare affected node subnets, pod IP allocation, and Azure network policy enforcement.

Section: AKS managed identity delay
AKS managed identity synchronization delays can cause controllers or CSI drivers to receive authorization failures immediately after identity or role-assignment changes. Confirm the role assignment, wait for propagation, and retry the controller action before rotating credentials.

Section: Post-mortem pattern signals
Kubernetes post-mortems often show cascades where a small configuration change triggers retries, log floods, DNS timeouts, node pressure, and evictions. The evaluation should reward answers that identify the first failing component and the downstream blast radius.

Section: Escalation boundary
Escalate to platform or cloud-provider support when control-plane APIs are unreachable across multiple clients, managed add-ons fail after rollback, cloud volume operations are stuck beyond the provider SLA, or multiple nodes in different zones become NotReady without a local change.
""",
}


def _source(document: str, section: str, text: str) -> dict[str, str]:
    return {"document": document, "section": section, "text": text}


SOURCE_STRATEGY = (
    "The Kubernetes troubleshooting knowledge base should prioritize the official "
    "Kubernetes debugging tasks, API reference, and kubectl command reference before "
    "community blogs, practical problem repositories, Kubernetes failure stories, and "
    "post-mortems. Managed service notes for EKS, GKE, and AKS should be layered after "
    "the core Kubernetes material."
)
TRIAGE_PACKET = (
    "Every Kubernetes incident ticket should include the namespace, workload name and "
    "kind, affected node, image tag, recent deployment time, exact user-visible symptom, "
    "kubectl get output, kubectl describe output, relevant events, pod logs, and any "
    "recent configuration or secret changes. Secrets, tokens, and customer payloads "
    "must be redacted."
)
PENDING = (
    "When a pod remains Pending, inspect kubectl describe pod events first. Common "
    "causes are insufficient CPU or memory, unsatisfied node selectors or affinity, "
    "taints without tolerations, missing persistent volumes, and image pull secrets "
    "that are referenced but not present."
)
CRASH_LOOP = (
    "For CrashLoopBackOff, compare the current container logs with kubectl logs "
    "--previous. Check the exit code, command arguments, environment variables, "
    "mounted configuration, liveness probe behavior, and whether the process exits "
    "before the readiness gate can succeed."
)
IMAGE_PULL = (
    "ImagePullBackOff usually means the kubelet cannot fetch the image. Validate the "
    "image name and tag, registry reachability, imagePullSecrets, service account "
    "permissions, and whether the registry is throttling or returning authentication failures."
)
CONFIG_ERROR = (
    "CreateContainerConfigError commonly indicates that the pod spec references a "
    "missing ConfigMap, missing Secret, invalid key, or malformed environment variable "
    "source. Describe the pod and compare referenced names and keys with the objects "
    "in the same namespace."
)
NODE_PRESSURE = (
    "Node pressure evictions are driven by kubelet thresholds for memory, disk, PID, "
    "or ephemeral storage pressure. Inspect node conditions, eviction events, container "
    "ephemeral-storage usage, log growth, and whether requests and limits reflect actual "
    "workload behavior."
)
CONTROL_PLANE = (
    "Control-plane troubleshooting starts with kube-apiserver reachability, etcd health, "
    "scheduler and controller-manager status, certificate validity, and admission webhook "
    "latency. Avoid restarting multiple control-plane components at once unless an approved "
    "recovery runbook requires it."
)
SERVICE_ENDPOINTS = (
    "If a Service has no endpoints, compare the Service selector with pod labels and "
    "confirm matching pods are Ready. A typo in app labels, readiness probe failures, "
    "or selecting pods in the wrong namespace can leave the Service without usable backends."
)
DNS_FAILURE = (
    "For DNS failures, verify CoreDNS pods are Running and Ready, inspect CoreDNS logs, "
    "test resolution from a temporary debug pod, confirm the Service name and namespace, "
    "and check NetworkPolicies that could block traffic to kube-dns."
)
NETWORK_POLICY = (
    "NetworkPolicy is namespace scoped and becomes restrictive for selected pods once "
    "ingress or egress policies apply. Debug by checking pod labels, namespace labels, "
    "policy podSelector, policyTypes, ports, and whether the CNI plugin enforces NetworkPolicy."
)
INGRESS = (
    "Ingress failures should be split between DNS, load balancer, ingress controller, "
    "TLS secret, class annotation or ingressClassName, backend Service mapping, and pod "
    "readiness. Controller logs usually reveal whether the route was accepted or rejected."
)
PVC_PENDING = (
    "A PersistentVolumeClaim remains Pending when no matching PersistentVolume exists "
    "or dynamic provisioning cannot satisfy the request. Check storageClassName, access "
    "modes, requested size, provisioner events, quota, and cloud-provider volume limits."
)
VOLUME_ATTACH = (
    "Volume attach and detach failures often involve stale node attachments, zone "
    "mismatch, cloud API throttling, CSI driver errors, or a previous pod still terminating. "
    "Confirm the pod node, volume zone, VolumeAttachment objects, CSI controller logs, "
    "and cloud-provider events."
)
AUTOSCALING = (
    "HorizontalPodAutoscaler decisions depend on metrics availability, target utilization, "
    "resource requests, and stabilization windows. If replicas do not change, check "
    "metrics-server health, HPA conditions, pod resource requests, and whether maxReplicas "
    "has already been reached."
)
SAFE_DEBUGGING = (
    "Use kubectl debug or ephemeral containers for live inspection when possible. Avoid "
    "editing live Deployments without recording the change, avoid deleting PersistentVolumeClaims "
    "during diagnosis, and avoid collecting full environment dumps that may contain secrets."
)
EKS_NETWORKING = (
    "On EKS, pod networking failures often trace to AWS VPC CNI IP exhaustion, subnet "
    "address shortage, security group rules, route table drift, or IAM permissions for "
    "the CNI daemonset. Check aws-node logs and available subnet IP addresses before "
    "recreating nodes."
)
EKS_AUTH = (
    "EKS authentication failures can come from aws-auth ConfigMap drift, IAM role mapping "
    "mistakes, expired client credentials, or API server authentication webhook latency. "
    "Verify the caller identity and the aws-auth role or user mapping before changing RBAC."
)
GKE_AUTOPILOT = (
    "On GKE Autopilot, scheduling can fail when requested resources, privileged settings, "
    "hostPath mounts, or unsupported security contexts violate Autopilot constraints. "
    "Review the admission error and adjust the workload rather than assuming node capacity "
    "is missing."
)
GKE_LOGGING = (
    "GKE logging agent anomalies can amplify node disk pressure when log volume spikes. "
    "Inspect container log growth, node filesystem usage, logging agent status, and whether "
    "noisy workloads need log sampling or rate reduction."
)
AKS_CNI = (
    "On AKS with Azure CNI, pod connectivity issues may stem from subnet IP exhaustion, "
    "network security group rules, user-defined routes, or route propagation delays. Compare "
    "affected node subnets, pod IP allocation, and Azure network policy enforcement."
)
AKS_IDENTITY = (
    "AKS managed identity synchronization delays can cause controllers or CSI drivers to "
    "receive authorization failures immediately after identity or role-assignment changes. "
    "Confirm the role assignment, wait for propagation, and retry the controller action "
    "before rotating credentials."
)
POSTMORTEMS = (
    "Kubernetes post-mortems often show cascades where a small configuration change "
    "triggers retries, log floods, DNS timeouts, node pressure, and evictions. The evaluation "
    "should reward answers that identify the first failing component and the downstream blast radius."
)
ESCALATION = (
    "Escalate to platform or cloud-provider support when control-plane APIs are unreachable "
    "across multiple clients, managed add-ons fail after rollback, cloud volume operations "
    "are stuck beyond the provider SLA, or multiple nodes in different zones become NotReady "
    "without a local change."
)


def _case(
    case_id: str,
    question: str,
    ground_truth: str,
    category: str,
    sources: list[dict[str, str]],
    *,
    answerable: bool = True,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": case_id,
        "application": "kubernetes_troubleshooting",
        "question": question,
        "ground_truth": ground_truth,
        "reference_contexts": [source["text"] for source in sources],
        "expected_sources": [
            {"document": source["document"], "section": source["section"]}
            for source in sources
        ],
        "category": category,
        "answerable": answerable,
        "tags": tags or [],
    }


def build_cases() -> list[dict[str, Any]]:
    cluster = "cluster_debugging_runbook.txt"
    workload = "workload_network_storage_guide.txt"
    managed = "managed_kubernetes_failure_notes.txt"
    return [
        _case("K8S-EVAL-001", "Which sources should the Kubernetes troubleshooting knowledge base prioritize first?", SOURCE_STRATEGY, "factoid", [_source(cluster, "Knowledge base source strategy", SOURCE_STRATEGY)], tags=["kubernetes", "source-priority"]),
        _case("K8S-EVAL-002", "What fields belong in the initial triage packet for a Kubernetes incident?", TRIAGE_PACKET, "procedural", [_source(cluster, "Initial triage packet", TRIAGE_PACKET)], tags=["kubernetes", "triage"]),
        _case("K8S-EVAL-003", "What should be checked first when a pod stays Pending?", "Inspect kubectl describe pod events first, then check CPU or memory scarcity, selectors, affinity, taints, tolerations, persistent volumes, and referenced image pull secrets.", "procedural", [_source(cluster, "Pending pods", PENDING)], tags=["kubernetes", "pods", "scheduling"]),
        _case("K8S-EVAL-004", "How should CrashLoopBackOff be investigated?", "Compare current logs with kubectl logs --previous, then inspect exit code, command arguments, environment variables, mounted configuration, liveness probes, and readiness timing.", "procedural", [_source(cluster, "CrashLoopBackOff", CRASH_LOOP)], tags=["kubernetes", "pods", "logs"]),
        _case("K8S-EVAL-005", "What does ImagePullBackOff usually indicate?", "It usually means the kubelet cannot fetch the image because of an invalid image, registry reachability, imagePullSecrets, service account permissions, throttling, or authentication failure.", "factoid", [_source(cluster, "ImagePullBackOff", IMAGE_PULL)], tags=["kubernetes", "images"]),
        _case("K8S-EVAL-006", "What usually causes CreateContainerConfigError?", "It commonly comes from a missing ConfigMap, missing Secret, invalid key, or malformed environment variable source referenced by the pod spec.", "factoid", [_source(cluster, "CreateContainerConfigError", CONFIG_ERROR)], tags=["kubernetes", "configuration"]),
        _case("K8S-EVAL-007", "Which signals should be inspected for node pressure evictions?", "Inspect node conditions, eviction events, ephemeral-storage usage, log growth, and whether requests and limits match workload behavior.", "procedural", [_source(cluster, "Node pressure and evictions", NODE_PRESSURE)], tags=["kubernetes", "node-pressure"]),
        _case("K8S-EVAL-008", "What is the safe starting point for control-plane troubleshooting?", "Start with kube-apiserver reachability, etcd health, scheduler and controller-manager status, certificate validity, and admission webhook latency.", "procedural", [_source(cluster, "Control plane health", CONTROL_PLANE)], tags=["kubernetes", "control-plane"]),
        _case("K8S-EVAL-009", "A Service has no endpoints. What comparisons should be made?", "Compare the Service selector with pod labels and confirm that matching pods are Ready and in the intended namespace.", "procedural", [_source(workload, "Service has no endpoints", SERVICE_ENDPOINTS)], tags=["kubernetes", "service"]),
        _case("K8S-EVAL-010", "How should in-cluster DNS resolution failure be debugged?", "Verify CoreDNS pods, inspect CoreDNS logs, test from a temporary debug pod, confirm Service name and namespace, and check policies blocking kube-dns.", "procedural", [_source(workload, "DNS resolution failure", DNS_FAILURE)], tags=["kubernetes", "dns"]),
        _case("K8S-EVAL-011", "What must be checked when NetworkPolicy unexpectedly blocks traffic?", "Check pod labels, namespace labels, podSelector, policyTypes, ports, and whether the CNI plugin enforces NetworkPolicy.", "procedural", [_source(workload, "NetworkPolicy isolation", NETWORK_POLICY)], tags=["kubernetes", "network-policy"]),
        _case("K8S-EVAL-012", "How should an Ingress outage be decomposed?", "Separate DNS, load balancer, ingress controller, TLS secret, ingress class, backend Service mapping, and pod readiness, then inspect controller logs.", "procedural", [_source(workload, "Ingress routing", INGRESS)], tags=["kubernetes", "ingress"]),
        _case("K8S-EVAL-013", "Why can a PersistentVolumeClaim remain Pending?", "No matching PersistentVolume may exist, or dynamic provisioning cannot satisfy storage class, access mode, size, quota, provisioner, or cloud volume constraints.", "factoid", [_source(workload, "PersistentVolumeClaim Pending", PVC_PENDING)], tags=["kubernetes", "storage"]),
        _case("K8S-EVAL-014", "What evidence should be gathered for volume attach or detach failures?", "Confirm the pod node, volume zone, VolumeAttachment objects, CSI controller logs, and cloud-provider events.", "procedural", [_source(workload, "Volume attach or detach failure", VOLUME_ATTACH)], tags=["kubernetes", "storage", "csi"]),
        _case("K8S-EVAL-015", "Why might an HPA not change replica count?", "The HPA may lack metrics, target utilization may not be reached, resource requests may be missing, stabilization windows may apply, or maxReplicas may already be reached.", "reasoning", [_source(workload, "Autoscaling mismatch", AUTOSCALING)], tags=["kubernetes", "autoscaling"]),
        _case("K8S-EVAL-016", "What production debugging actions should be avoided?", "Avoid unrecorded live Deployment edits, deleting PersistentVolumeClaims during diagnosis, and collecting full environment dumps that may contain secrets.", "safety", [_source(workload, "Safe production debugging", SAFE_DEBUGGING)], tags=["kubernetes", "safety"]),
        _case("K8S-EVAL-017", "On EKS, what should be checked before recreating nodes for pod networking failures?", "Check aws-node logs and available subnet IP addresses, because failures often involve VPC CNI IP exhaustion, subnet shortage, security groups, routes, or IAM permissions.", "procedural", [_source(managed, "EKS networking faults", EKS_NETWORKING)], tags=["kubernetes", "eks", "networking"]),
        _case("K8S-EVAL-018", "What should be verified before changing RBAC for an EKS authentication failure?", "Verify the caller identity and aws-auth role or user mapping before changing RBAC.", "procedural", [_source(managed, "EKS IAM authentication", EKS_AUTH)], tags=["kubernetes", "eks", "auth"]),
        _case("K8S-EVAL-019", "How should GKE Autopilot scheduling denials be handled?", "Review the admission error and adjust resources or unsupported settings instead of assuming normal node capacity is missing.", "reasoning", [_source(managed, "GKE Autopilot scheduling limits", GKE_AUTOPILOT)], tags=["kubernetes", "gke", "scheduling"]),
        _case("K8S-EVAL-020", "How can a GKE logging anomaly cascade into node pressure?", "A logging agent anomaly can amplify disk pressure when log volume spikes, so inspect log growth, filesystem usage, logging agent status, and noisy workloads.", "multi_hop", [_source(managed, "GKE logging agent pressure", GKE_LOGGING), _source(cluster, "Node pressure and evictions", NODE_PRESSURE)], tags=["kubernetes", "gke", "node-pressure"]),
        _case("K8S-EVAL-021", "On AKS with Azure CNI, what can cause pod connectivity problems?", "Subnet IP exhaustion, network security group rules, user-defined routes, route propagation delays, pod IP allocation, or network policy enforcement can cause connectivity issues.", "factoid", [_source(managed, "AKS Azure CNI routing", AKS_CNI)], tags=["kubernetes", "aks", "networking"]),
        _case("K8S-EVAL-022", "What should be done after AKS identity or role-assignment changes trigger CSI authorization failures?", "Confirm the role assignment, wait for propagation, and retry the controller action before rotating credentials.", "procedural", [_source(managed, "AKS managed identity delay", AKS_IDENTITY)], tags=["kubernetes", "aks", "identity"]),
        _case("K8S-EVAL-023", "What pattern should the evaluator reward in Kubernetes post-mortem answers?", "Reward answers that identify the first failing component and downstream blast radius across retries, log floods, DNS timeouts, node pressure, and evictions.", "reasoning", [_source(managed, "Post-mortem pattern signals", POSTMORTEMS)], tags=["kubernetes", "postmortem"]),
        _case("K8S-EVAL-024", "When should a Kubernetes issue be escalated to platform or cloud-provider support?", ESCALATION, "procedural", [_source(managed, "Escalation boundary", ESCALATION)], tags=["kubernetes", "escalation"]),
        _case("K8S-EVAL-025", "A pod is Pending and its PVC is also Pending. Which root causes should be investigated together?", "Investigate scheduling events plus storage provisioning: node resources, selectors, taints, missing volumes, storageClassName, access modes, requested size, quota, provisioner events, and cloud volume limits.", "multi_hop", [_source(cluster, "Pending pods", PENDING), _source(workload, "PersistentVolumeClaim Pending", PVC_PENDING)], tags=["kubernetes", "scheduling", "storage"]),
        _case("K8S-EVAL-026", "A Service has no endpoints after a rollout and users see Ingress 503s. What should be checked first?", "Check whether the Service selector still matches Ready pods, then validate backend Service mapping and pod readiness from the Ingress path.", "multi_hop", [_source(workload, "Service has no endpoints", SERVICE_ENDPOINTS), _source(workload, "Ingress routing", INGRESS)], tags=["kubernetes", "service", "ingress"]),
        _case("K8S-EVAL-027", "A CrashLoopBackOff started after a ConfigMap change. Which evidence connects the two?", "Use previous logs and exit code, then compare mounted configuration and referenced ConfigMap or Secret keys in the same namespace.", "multi_hop", [_source(cluster, "CrashLoopBackOff", CRASH_LOOP), _source(cluster, "CreateContainerConfigError", CONFIG_ERROR)], tags=["kubernetes", "configuration", "pods"]),
        _case("K8S-EVAL-028", "Is it safe to collect a full environment dump from a production pod to debug an incident?", "No. Full environment dumps may contain secrets; use safer live debugging and redact secrets, tokens, and customer payloads.", "safety", [_source(workload, "Safe production debugging", SAFE_DEBUGGING), _source(cluster, "Initial triage packet", TRIAGE_PACKET)], tags=["kubernetes", "safety", "triage"]),
        _case("K8S-EVAL-029", "Which Helm chart version fixes the documented CoreDNS timeout issue?", "The supplied Kubernetes troubleshooting documents do not identify a Helm chart version for a CoreDNS timeout fix.", "unanswerable", [], answerable=False, tags=["kubernetes", "negative"]),
        _case("K8S-EVAL-030", "What is the monthly price of a larger managed Kubernetes node pool?", "The supplied Kubernetes troubleshooting documents do not contain managed node pool pricing.", "unanswerable", [], answerable=False, tags=["kubernetes", "negative"]),
    ]


def generate(dataset_path: Path, source_dir: Path) -> None:
    source_dir.mkdir(parents=True, exist_ok=True)
    dataset_path.parent.mkdir(parents=True, exist_ok=True)

    for filename, content in SOURCE_DOCUMENTS.items():
        (source_dir / filename).write_text(content, encoding="utf-8")

    with dataset_path.open("w", encoding="utf-8", newline="\n") as handle:
        for case in build_cases():
            handle.write(json.dumps(case, ensure_ascii=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    args = parser.parse_args()
    generate(args.output, args.source_dir)
    print(f"Generated 30 Kubernetes cases at {args.output}")
    print(f"Generated {len(SOURCE_DOCUMENTS)} source documents at {args.source_dir}")


if __name__ == "__main__":
    main()
