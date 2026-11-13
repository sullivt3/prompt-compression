"use strict";
(() => {
  const $ = (id) => document.getElementById(id);
  const form = $("compression-form");
  const prompt = $("prompt");
  const examples = {
    simple: "Hey ChatGPT, can you please explain what Kubernetes is?",
    technical: "I would like you to explain how Docker containers differ from virtual machines.",
    filler: "Paste a prompt below. This is just a test to see how many filler words can be removed form the input.",
    mixed: 'Can you please provide an explanation of this function?\n\n```python\ndef add(a, b):\n    return a + b\n```\n\nProvide an explanation of addition in order to teach a beginner.',
    courtesy: "Hi there, sorry to bother you, can you please explain Docker. Thanks!",
    protected: 'Explain this configuration without changing any values:\n```json\n{"replicas": 3, "enabled": true}\n```',
  };
  const reasons = {
    protected_content: "Protected content detected. The original prompt was preserved.",
    protected_role: "This message role is protected from compression.",
    ambiguous_protected_content: "A protected section has an uncertain boundary or syntax. The entire original prompt was preserved.",
    ambiguous_content: "The content could not be safely classified. The original was preserved.",
    no_approved_transformation: "No further approved transformations match this input. If it is already shortened, try the original prompt using the Filler-word test example.",
    validation_failed: "The candidate did not pass validation or minimum savings thresholds. The original was preserved.",
    disabled: "Compression is off. Select Algorithmic in the Strategy menu to compress your prompt.",
    compression_error: "Compression encountered an error. The original prompt was preserved.",
    transformation_budget: "The transformation limit was reached. The original prompt was preserved.",
    empty: "The prompt is empty.",
  };
  const numbers = new Intl.NumberFormat();
  let busy = false;
  let lastResult = null;
  let lastInput = null;

  function setStatus(message, error = false) {
    $("status").textContent = message;
    $("status").classList.toggle("error", error);
  }
  function updateSubmitState() {
    const hasKey = Boolean($("api-key").value.trim());
    $("submit").disabled = busy || !hasKey;
    $("submit").title = hasKey ? "" : "Enter a gateway API key first";
    $("submit-label").textContent = busy ? "Compressing…" : (hasKey ? "Compress prompt" : "Enter API key to compress");
  }
  function keyChanged() {
    updateSubmitState();
    if (!busy) {
      setStatus($("api-key").value.trim() ? "Ready to compress. No LLM calls are made." : "Enter your gateway API key to enable compression.");
    }
  }
  $("api-key").addEventListener("input", keyChanged);
  $("api-key").addEventListener("change", keyChanged);
  function resetResult() {
    lastResult = null;
    lastInput = null;
    $("empty-state").hidden = false;
    $("optimized").hidden = true;
    $("optimized").textContent = "";
    $("result-badge").hidden = true;
    $("details-panel").hidden = true;
    $("copy").disabled = true;
    $("result-note").textContent = "Ready when you are";
    ["original-tokens", "optimized-tokens", "saved-tokens", "compression-time"].forEach((id) => { $(id).textContent = "—"; });
    $("reduction").textContent = "Waiting for a prompt";
    $("request-time").textContent = "Server processing only";
  }
  function inputChanged() {
    $("character-count").textContent = `${numbers.format(prompt.value.length)} characters`;
    if (lastInput && (prompt.value !== lastInput.text || $("model").value.trim() !== lastInput.model || $("strategy").value !== lastInput.strategy)) {
      resetResult();
      setStatus("Input changed. Compress again to see an up-to-date comparison.");
    }
  }
  prompt.addEventListener("input", inputChanged);
  $("model").addEventListener("input", inputChanged);
  $("strategy").addEventListener("change", inputChanged);
  document.querySelectorAll("[data-example]").forEach((button) => {
    button.addEventListener("click", () => {
      prompt.value = examples[button.dataset.example];
      inputChanged();
      prompt.focus();
    });
  });
  $("clear").addEventListener("click", () => {
    prompt.value = "";
    resetResult();
    inputChanged();
    setStatus("No LLM calls. No generated answers. Just a leaner prompt.");
    prompt.focus();
  });
  $("copy").addEventListener("click", async () => {
    if (!lastResult) return;
    try {
      await navigator.clipboard.writeText(lastResult.optimized);
      setStatus("Compressed prompt copied to clipboard.");
    } catch {
      setStatus("Clipboard access is unavailable. Select and copy the result directly.", true);
    }
  });
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (busy) return;
    if (!prompt.value.trim()) {
      setStatus("Enter a prompt to compress.", true);
      prompt.focus();
      return;
    }
    const key = $("api-key").value.trim();
    if (!key) {
      document.querySelector(".connection").open = true;
      $("api-key").focus();
      setStatus("Enter your gateway API key to run a compression preview.", true);
      return;
    }
    if (!form.reportValidity()) return;
    const payload = {text: prompt.value, model: $("model").value.trim(), strategy: $("strategy").value};
    resetResult();
    busy = true;
    form.setAttribute("aria-busy", "true");
    form.querySelectorAll("button, textarea, input, select").forEach((control) => { control.disabled = true; });
    updateSubmitState();
    setStatus("Analyzing your prompt and checking safe transformations…");
    const start = performance.now();
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 30000);
    try {
      const response = await fetch("/v1/optimize", {
        method: "POST", headers: {"Content-Type": "application/json", "Authorization": `Bearer ${key}`},
        body: JSON.stringify(payload), signal: controller.signal, cache: "no-store", redirect: "error",
      });
      const elapsed = performance.now() - start;
      const data = await response.json();
      if (!response.ok) {
        const errors = {
          401: "The gateway API key is invalid, expired, or revoked.",
          429: "The request or concurrency limit was reached. Wait a moment and try again.",
          503: "The gateway dependencies are unavailable. Check PostgreSQL and Redis, then try again.",
          422: "The request could not be processed. Check the model identifier and strategy.",
        };
        throw new Error(errors[response.status] || data.error?.message || `Request failed (${response.status}).`);
      }
      if (typeof data.optimized !== "string" || !Number.isFinite(data.original_tokens) || !Number.isFinite(data.optimized_tokens) || !Number.isFinite(data.saved_tokens) || !Number.isFinite(data.optimization_latency_ms) || !Number.isFinite(data.reduction_percent)) {
        throw new Error("The gateway returned an unexpected preview response.");
      }
      lastResult = data;
      lastInput = payload;
      $("empty-state").hidden = true;
      $("optimized").textContent = data.optimized;
      $("optimized").hidden = false;
      $("result-badge").textContent = data.applied ? "COMPRESSED" : "UNCHANGED";
      $("result-badge").hidden = false;
      $("result-note").textContent = data.applied ? "Validated algorithmic result" : "Original prompt preserved";
      $("original-tokens").textContent = numbers.format(data.original_tokens);
      $("optimized-tokens").textContent = numbers.format(data.optimized_tokens);
      $("saved-tokens").textContent = numbers.format(data.saved_tokens);
      $("reduction").textContent = `${data.reduction_percent.toFixed(1)}% fewer input tokens`;
      $("compression-time").textContent = `${data.optimization_latency_ms.toFixed(2)} ms`;
      $("request-time").textContent = `${elapsed.toFixed(0)} ms total request time`;
      $("tokenizer").textContent = `Tokenizer: ${data.tokenizer}`;
      $("decision").textContent = data.applied ? "An eligible candidate passed the configured validation and savings thresholds. These checks do not prove semantic equivalence." : (reasons[data.skip_reason] || "The original prompt was preserved under the current policy.");
      $("rules").replaceChildren();
      (data.rules_applied || []).forEach((rule) => {
        const badge = document.createElement("span");
        badge.textContent = rule.replaceAll("_", " ");
        $("rules").append(badge);
      });
      $("validation").textContent = JSON.stringify({validation: data.validation, transformations: data.transformations, skip_reason: data.skip_reason}, null, 2);
      $("details-panel").hidden = false;
      setStatus(data.applied
        ? `Compressed ${numbers.format(data.original_tokens)} → ${numbers.format(data.optimized_tokens)} tokens. Saved ${numbers.format(data.saved_tokens)} tokens (${data.reduction_percent.toFixed(1)}%). No LLM was called.`
        : `${reasons[data.skip_reason] || "The original prompt was preserved under the current policy."} Submitted input: ${numbers.format(data.original_tokens)} tokens.`);
    } catch (error) {
      setStatus(error.name === "AbortError" ? "The request timed out. Please try again." : (error instanceof TypeError ? "Could not reach the gateway. Check the connection and try again." : error.message), true);
    } finally {
      clearTimeout(timeout);
      busy = false;
      form.removeAttribute("aria-busy");
      form.querySelectorAll("button, textarea, input, select").forEach((control) => { control.disabled = false; });
      $("copy").disabled = !lastResult;
      updateSubmitState();
    }
  });
  inputChanged();
  keyChanged();
})();
