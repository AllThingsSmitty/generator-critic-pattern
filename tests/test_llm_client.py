from shared.llm_client import TokenBudget, Usage, extract_code_block


class TestUsage:
    def test_total_tokens_sums_input_and_output(self) -> None:
        usage = Usage(input_tokens=100, output_tokens=50, model="claude-sonnet-5")
        assert usage.total_tokens == 150

    def test_cost_usd_known_model(self) -> None:
        # claude-sonnet-5: $2.00/1M in, $10.00/1M out
        usage = Usage(input_tokens=1_000_000, output_tokens=1_000_000, model="claude-sonnet-5")
        assert usage.cost_usd == 12.00

    def test_cost_usd_unknown_model_is_zero(self) -> None:
        usage = Usage(input_tokens=1_000_000, output_tokens=1_000_000, model="not-a-real-model")
        assert usage.cost_usd == 0.0


class TestTokenBudget:
    def test_record_accumulates_spend_and_log(self) -> None:
        budget = TokenBudget(max_total_tokens=1000)
        budget.record(Usage(100, 50, "claude-sonnet-5"))
        budget.record(Usage(200, 100, "claude-sonnet-5"))

        assert budget.spent_tokens == 450
        assert len(budget.usage_log) == 2

    def test_exceeded_false_under_cap(self) -> None:
        budget = TokenBudget(max_total_tokens=1000)
        budget.record(Usage(100, 50, "claude-sonnet-5"))
        assert budget.exceeded() is False

    def test_exceeded_true_at_or_over_cap(self) -> None:
        budget = TokenBudget(max_total_tokens=100)
        budget.record(Usage(80, 20, "claude-sonnet-5"))
        assert budget.exceeded() is True

    def test_remaining_floors_at_zero(self) -> None:
        budget = TokenBudget(max_total_tokens=100)
        budget.record(Usage(80, 40, "claude-sonnet-5"))
        assert budget.remaining() == 0

    def test_total_cost_usd_sums_logged_usage(self) -> None:
        budget = TokenBudget(max_total_tokens=10_000_000)
        budget.record(Usage(1_000_000, 0, "claude-sonnet-5"))  # $2.00
        budget.record(Usage(0, 1_000_000, "claude-haiku-4-5"))  # $5.00
        assert budget.total_cost_usd == 7.00


class TestExtractCodeBlock:
    def test_fenced_block_with_language_tag(self) -> None:
        text = "```python\ndef foo():\n    pass\n```"
        assert extract_code_block(text) == "def foo():\n    pass"

    def test_fenced_block_without_language_tag(self) -> None:
        text = "```\nhello\n```"
        assert extract_code_block(text) == "hello"

    def test_fenced_block_surrounded_by_prose(self) -> None:
        text = "Here's the code:\n```python\nx = 1\n```\nDone."
        assert extract_code_block(text) == "x = 1"

    def test_falls_back_to_raw_text_when_unfenced(self) -> None:
        text = "  just some text, no fence  "
        assert extract_code_block(text) == "just some text, no fence"

    def test_returns_only_first_block_when_multiple(self) -> None:
        text = "```\nfirst\n```\nsome text\n```\nsecond\n```"
        assert extract_code_block(text) == "first"

    def test_empty_fenced_block(self) -> None:
        text = "```\n\n```"
        assert extract_code_block(text) == ""
