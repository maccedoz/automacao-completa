import os
import csv
import random
import re
import asyncio  # <<< MUDANÇA <<<: Importado para concorrência
from pathlib import Path
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage
from langchain_together import ChatTogether

# --- Configuration ---
load_dotenv()

DATA_FOLDER = "test_smell_docs"
OUTPUT_CSV_FILE = "resultado.csv"

TEST_SMELL_TYPES = [
    "Duplicate Assert", "Assertion Roulette", "Magic Number Test",
    "Eager Test", "Ignored Test", "Unknown Test", "Verbose Test",
    "Conditional Test Logic", "Exception Catching Throwing", "Sensitive Equality"
]

PROMPT_TEMPLATE = """
Context: "Test smells" are defined as antipatterns or "bad programming practices" in unit test code, indicating potential design problems in the test's source code. Although these tests are not exactly bugs that break compilation or cause the test to fail, they indicate deeper design issues, including readability, comprehensibility, and maintainability.

Among the best-known "Test Smells" are:

Duplicate Assert: This smell occurs when a test method tests for the same condition multiple times within the same test method. If the test method needs to test the same condition using different values, a new test method should be created. 

Example:
```java
@Test
  public void testApplyUdfWithPathButNoFunction() {{
    PubSubProtoToBigQueryOptions options = getOptions();
    options.setJavascriptTextTransformGcsPath("/some/path.js");
    PCollection<String> input = pipeline.apply(Create.of(""));

    assertThrows(IllegalArgumentException.class, () -> runUdf(input, options));
    options.setJavascriptTextTransformFunctionName("");
    assertThrows(IllegalArgumentException.class, () -> runUdf(input, options));

    pipeline.run();
  }}
```

Assertion Roulette: Occurs when a test method has multiple non-documented assertions. Multiple assertion statements in a test method without descriptive messages impact readability, understandability, and maintainability, as it’s not possible to understand the reason for the test failure.

Example:
```java
@Test
  public void rejectAlreadyAddedItem() {{
    CommandResultWithReply<
            ShoppingCart.Command,
            ShoppingCart.Event,
            ShoppingCart.State,
            StatusReply<ShoppingCart.Summary>>
        result1 =
            eventSourcedTestKit.runCommand(replyTo -> new ShoppingCart.AddItem("foo", 42, replyTo));
    assertTrue(result1.reply().isSuccess());
    CommandResultWithReply<
            ShoppingCart.Command,
            ShoppingCart.Event,
            ShoppingCart.State,
            StatusReply<ShoppingCart.Summary>>
        result2 =
            eventSourcedTestKit.runCommand(replyTo -> new ShoppingCart.AddItem("foo", 42, replyTo));
    assertTrue(result2.reply().isError());
    assertTrue(result2.hasNoEvents());
  }}
```

Magic Number Test: This smell occurs when a test method contains unexplained and undocumented numeric literals as parameters or as values to identifiers. These magic values do not sufficiently indicate the meaning or purpose of the number, hindering code understandability. They should be replaced with constants or variables that provide descriptive names for the values.

Example:
```java
@Test
  public void updateFromDifferentNodesViaGrpc() throws Exception {{
    // add from client1
    CompletionStage<Cart> response1 =
        testNode1
            .getClient()
            .addItem(
                AddItemRequest.newBuilder()
                    .setCartId("cart-1")
                    .setItemId("foo")
                    .setQuantity(42)
                    .build());
    Cart updatedCart1 = response1.toCompletableFuture().get(requestTimeout.getSeconds(), SECONDS);
    assertEquals("foo", updatedCart1.getItems(0).getItemId());
    assertEquals(42, updatedCart1.getItems(0).getQuantity());

    // add from client2
    CompletionStage<Cart> response2 =
        testNode2
            .getClient()
            .addItem(
                AddItemRequest.newBuilder()
                    .setCartId("cart-2")
                    .setItemId("bar")
                    .setQuantity(17)
                    .build());
    Cart updatedCart2 = response2.toCompletableFuture().get(requestTimeout.getSeconds(), SECONDS);
    assertEquals("bar", updatedCart2.getItems(0).getItemId());
    assertEquals(17, updatedCart2.getItems(0).getQuantity());
  }}
```

Eager Test: A test case that checks or uses more than one method of the class under test. It is left to interpretation which method calls count towards this smell. Either all methods invoked on the class under test could count, or only methods whose return values are eventually used in assertions. It may or may not have the @Ignore annotation.

Example:
```java
@Test
  public void testBeamWindowedValueEncoderMappings() {{
    BASIC_CASES.forEach(
        (coder, data) -> {{
          List<WindowedValue<?>> windowed =
              Lists.transform(data, WindowedValues::valueInGlobalWindow);

          Encoder<?> encoder = windowedValueEncoder(encoderFor(coder), windowEnc);
          serializeAndDeserialize(windowed.get(0), (Encoder) encoder);

          Dataset<?> dataset = createDataset(windowed, (Encoder) encoder);
          assertThat(dataset.collect(), equalTo(windowed.toArray()));
        }});
  }}
```

Ignored Test: JUnit 4 provides developers with the ability to suppress test methods from running. However, these ignored test methods add unnecessary compilation overhead and increase code complexity and comprehension burden.

Example:
```java
@Test
private void testCanceledPipeline(final SparkStructuredStreamingPipelineOptions options)
      throws Exception {{

    final Pipeline pipeline = getPipeline(options);

    final SparkStructuredStreamingPipelineResult result =
        (SparkStructuredStreamingPipelineResult) pipeline.run();

    result.cancel();

    assertThat(result.getState(), is(PipelineResult.State.CANCELLED));
  }}
```

Unknown Test: An assertion statement is used to declare an expected boolean condition for a test method. However, it’s possible for a test method to be written without any assertions. In this case, JUnit will show the test as passing if no exceptions are thrown, making it hard to understand the purpose of the test.

Example:
```java
@Test
public void hitGetPOICategoriesApi() throws Exception {{
    POICategories poiCategories = apiClient.getPOICategories(16);
    for (POICategory category : poiCategories) {{
        System.out.println(category.name() + ": " + category);
    }}
}}
```

Verbose Test: A test method with more than 30 lines. It may indicate multiple responsibilities, affecting test maintainability.

Example:
```java
@Test
  public void safelyUpdatePopularityCount() throws Exception {{
    ClusterSharding sharding = ClusterSharding.get(system);

    final String item = "concurrent-item";
    int cartCount = 30;
    int itemCount = 1;
    final Duration timeout = Duration.ofSeconds(30);

    // Given `item1` is already on the popularity projection DB...
    CompletionStage<ShoppingCart.Summary> rep1 =
        sharding
            .entityRefFor(ShoppingCart.ENTITY_KEY, "concurrent-cart0")
            .askWithStatus(replyTo -> new ShoppingCart.AddItem(item, itemCount, replyTo), timeout);

    TestProbe<Object> probe = testKit.createTestProbe();
    probe.awaitAssert(
        () -> {{
          Optional<ItemPopularity> item1Popularity = itemPopularityRepository.findById(item);
          assertTrue(item1Popularity.isPresent());
          assertEquals(itemCount, item1Popularity.get().getCount());
          return null;
        }});

    // ... when 29 concurrent carts add `item1`...
    for (int i = 1; i < cartCount; i++) {{
      sharding
          .entityRefFor(ShoppingCart.ENTITY_KEY, "concurrent-cart" + i)
          .<ShoppingCart.Summary>askWithStatus(
              replyTo -> new ShoppingCart.AddItem(item, itemCount, replyTo), timeout);
    }}

    // ... then the popularity count is 30
    probe.awaitAssert(
        timeout,
        () -> {{
          Optional<ItemPopularity> item1Popularity = itemPopularityRepository.findById(item);
          assertTrue(item1Popularity.isPresent());
          assertEquals(cartCount * itemCount, item1Popularity.get().getCount());
          return null;
        }});
  }}
```

Conditional Logic Test: Test methods should be simple and execute all statements in the production method. Conditional logic in tests alters behavior and can hide defects. It also reduces test readability.

Example:
```java
@Test
  public void testServiceLoaderForOptions() {{
    for (PipelineOptionsRegistrar registrar :
        Lists.newArrayList(ServiceLoader.load(PipelineOptionsRegistrar.class).iterator())) {{
      if (registrar instanceof SparkStructuredStreamingRunnerRegistrar.Options) {{
        return;
      }}
    }}
    fail("Expected to find " + SparkStructuredStreamingRunnerRegistrar.Options.class);
  }}
```

Sensitive Equality: Occurs when the toString() method is used within a test method to compare objects. If the toString() implementation changes, the test may fail unnecessarily. The correct approach is to implement a dedicated equality-checking method.

Example:
```java
@Test
  public void testWindowedDirectorySinglePattern() {{

  
      ResourceId outputDirectory =
        getBaseTempDirectory()
            .resolve("recommendations/mmmm/", StandardResolveOptions.RESOLVE_DIRECTORY);
    IntervalWindow window = mock(IntervalWindow.class);
    PaneInfo paneInfo = PaneInfo.createPane(false, true, Timing.ON_TIME, 0, 0);

    Instant windowBegin = new DateTime(2017, 1, 8, 10, 55, 0).toInstant();
    Instant windowEnd = new DateTime(2017, 1, 8, 10, 56, 0).toInstant();
    when(window.maxTimestamp()).thenReturn(windowEnd);
    when(window.start()).thenReturn(windowBegin);
    when(window.end()).thenReturn(windowEnd);

    WindowedFilenamePolicy policy =
        WindowedFilenamePolicy.writeWindowedFiles()
            .withOutputDirectory(outputDirectory.toString())
            .withOutputFilenamePrefix("output")
            .withShardTemplate("-SSS-of-NNN")
            .withSuffix("")
            .withMinutePattern("mmmm");

    ResourceId filename =
        policy.windowedFilename(1, 1, window, paneInfo, new TestOutputFileHints());

    assertThat(filename).isNotNull();
    assertThat(filename.getCurrentDirectory().toString()).endsWith("recommendations/0056/");
    assertThat(filename.getFilename()).isEqualTo("output-001-of-001");
  }}
```

Exception Catching Throwing:
Occurs when a test method explicitly uses try/catch blocks or manually throws exceptions to verify error behavior. This practice reduces readability and may hide real errors, since it relies on manual exception handling rather than the test framework’s built-in mechanisms. The correct approach is to use the framework’s native exception assertion methods (e.g., assertThrows in JUnit) to check for expected exceptions clearly and safely.

Example:
```java
@Test
  public void testColumnToValueTimestampInvalid() {{
    TableFieldSchema column =
        new TableFieldSchema().setName(invalidTimestampField).setType("TIMESTAMP");
    Record record =
        generateSingleFieldAvroRecord(
            invalidTimestampField,
            "long",
            invalidTimestampFieldDesc,
            invalidTimestampFieldValueNanos);
    boolean isThrown = false;
    try {{
      Value value = BigQueryConverters.columnToValue(column, record.get(invalidTimestampField));
    }} catch (IllegalArgumentException e) {{
      isThrown = true;
    }}
    assertTrue(isThrown);
  }}
```

You are a senior software engineer. From the definitions above, ANSWER the following question by choosing only ONE alternative, using ONLY the LETTER of the correct option.

Question: In the test code below, which type of "Test Smell" can be identified?

{test_code}

Alternatives:
A: {option_a}
B: {option_b}
C: {option_c}
D: {option_d}
E: None

Answer format: {{A}}

Directive: Provide only one alternative letter and DO NOT include any analysis about the code, only the corresponding letter of the answer.
"""

# --- Model Initialization ---
# Carrega variáveis de ambiente do .env
load_dotenv(dotenv_path=Path(".env"))


def initialize_models() -> dict:
    """
    Inicializa e retorna um dicionário com modelos de múltiplos provedores:
    - OpenAI
    - Together AI
    """
    models = {}

    # ✅ OPENAI
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        models.update({
            "openai_gpt5": ChatOpenAI(model="gpt-5", api_key=openai_key),
            "openai_gpt4.1": ChatOpenAI(model="gpt-4.1", api_key=openai_key),
            "openai_gpt4.1_nano": ChatOpenAI(model="gpt-4.1-nano", api_key=openai_key),
            "openai_gpt5_nano": ChatOpenAI(model="gpt-5-nano", api_key=openai_key),
        })

    # ✅ TOGETHER AI
    together_key_1 = os.getenv("TOGETHER_API_KEY_1")
    if together_key_1:
        models.update({
            "together_deepseek": ChatTogether(model="deepseek-ai/DeepSeek-R1-Distill-Llama-70B-free", api_key=together_key_1),
            "together_gemma": ChatTogether(model="google/gemma-3n-E4B-it", api_key=together_key_1),
            "together_qwen": ChatTogether(model="Qwen/Qwen2.5-7B-Instruct-Turbo", api_key=together_key_1),
        })
    
    together_key_2 = os.getenv("TOGETHER_API_KEY_2")
    if together_key_2:
        models.update({
            "together_llama": ChatTogether(model="meta-llama/Llama-3.3-70B-Instruct-Turbo-Free", api_key=together_key_2),
        })

    return models


# --- Data Extraction ---
def extract_tests_from_folder(folder_path: str) -> list:
    folder = Path(folder_path)
    if not folder.is_dir():
        raise FileNotFoundError(
            f"Error: The folder '{folder_path}' was not found.")

    extracted_tests = []
    print(f"Searching for test files in '{folder.resolve()}'...")

    files = list(folder.glob("*.txt"))
    if not files:
        print(f"Warning: No .txt files found in '{folder_path}'.")
        return []

    for file_path in files:
        true_test_smell = file_path.stem
        print(
            f"Reading file: '{file_path.name}' for smell: '{true_test_smell}'")

        content = file_path.read_text(encoding='utf-8')
        code_blocks = re.findall(
            r"```(?:java)?(.*?)```", content, re.DOTALL)

        if not code_blocks:
            print(
                f"  -> Warning: No code blocks found in '{file_path.name}'.")
            continue

        for code in code_blocks:
            extracted_tests.append({
                "source_file": file_path.name,
                "code_to_analyze": code.strip(),
                "correct_smell": true_test_smell
            })

    print(
        f"\nTotal of {len(extracted_tests)} tests extracted from {len(files)} files.\n")
    return extracted_tests

# --- Prompt Engineering ---

def create_randomized_prompt(code_snippet: str, correct_smell: str) -> tuple[str | None, str | None]:
    """Creates a multiple-choice prompt with one correct and three random incorrect options."""
    if correct_smell not in TEST_SMELL_TYPES:
        print(
            f"Warning: Test smell '{correct_smell}' not found in the predefined list. Skipping.")
        return None, None
    random.shuffle(TEST_SMELL_TYPES)
    other_smells = [s for s in TEST_SMELL_TYPES if s != correct_smell]
    incorrect_options = random.sample(other_smells, 3)

    options = [correct_smell] + incorrect_options
    random.shuffle(options)

    correct_letter = "ABCD"[options.index(correct_smell)]

    prompt = PROMPT_TEMPLATE.format(
        test_code=code_snippet,
        option_a=options[0],
        option_b=options[1],
        option_c=options[2],
        option_d=options[3]
    )

    return prompt, correct_letter

# --- LLM Interaction ---

# <<< MUDANÇA <<<: A função invoke_llm foi transformada em assíncrona
async def invoke_llm_async(prompt: str, model, model_name: str) -> tuple[str, str]:
    """
    Invoca o LLM de forma assíncrona e extrai a resposta de uma letra.
    Retorna uma tupla (model_name, response_letter).
    """
    print(f"  -> [INICIANDO] Querying model: {model_name}")
    try:
        # Usa .ainvoke() para chamada assíncrona
        response = await model.ainvoke(prompt)
        response_content = response.content.strip()

        match = re.search(r'([A-E])', response_content.upper())
        if match:
            print(f"  -> [CONCLUÍDO] Model: {model_name}")
            return (model_name, match.group(1))

        print(
            f"  -> Warning: Could not parse a valid letter from response: '{response_content}'")
        return (model_name, "PARSE_ERROR")

    except Exception as e:
        print(f"  -> Error invoking model {model_name}: {e}")
        return (model_name, "API_ERROR")

# --- File Operations ---


def save_results_to_csv(filename: str, results: list, headers: list):
    """Appends a list of dictionaries to a CSV file."""
    if not results:
        print("No results to save.")
        return

    is_new_file = not os.path.exists(
        filename) or os.path.getsize(filename) == 0
    try:
        with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            if is_new_file:
                writer.writeheader()
            writer.writerows(results)
        print(f"\n✅ Results successfully saved to '{filename}'")
    except Exception as e:
        print(f"\n❌ Error saving CSV file: {e}")

# --- Main Execution ---

# <<< MUDANÇA <<<: A função main agora é assíncrona (async def)
async def main():
    models = initialize_models()
    try:
        tests_to_process = extract_tests_from_folder(DATA_FOLDER)
    except FileNotFoundError as e:
        print(e)
        return

    all_results = []

    print("--- Starting cross-processing of tests and models ---")
    for i, test_data in enumerate(tests_to_process):
        print(
            f"Processing test {i+1}/{len(tests_to_process)} (from {test_data['source_file']})...")

        prompt, correct_letter = create_randomized_prompt(
            test_data["code_to_analyze"],
            test_data["correct_smell"]
        )

        if not prompt:
            continue

        result_row = {
            "test_smell": test_data["correct_smell"],
            "correct_answer": correct_letter
        }

        
        # 1. Cria uma lista de "tarefas" assíncronas
        tasks = []
        for model_name, model_instance in models.items():
            tasks.append(invoke_llm_async(prompt, model_instance, model_name))

        # 2. Executa todas as tarefas em paralelo
        # asyncio.gather() roda todas as corrotinas "ao mesmo tempo"
        # e espera que todas terminem.
        model_responses = await asyncio.gather(*tasks)

        # 3. Coleta os resultados
        # model_responses será uma lista de tuplas: [("openai_gpt5", "A"), ("together_llama", "B"), ...]
        for model_name, response in model_responses:
            result_row[model_name] = response

        all_results.append(result_row)

    model_columns = list(models.keys())
    csv_headers = ['test_smell', 'correct_answer'] + model_columns
    save_results_to_csv(OUTPUT_CSV_FILE, all_results, csv_headers)


# <<< MUDANÇA <<<: A forma de executar o script muda para rodar a função main assíncrona
if __name__ == "__main__":
    asyncio.run(main())