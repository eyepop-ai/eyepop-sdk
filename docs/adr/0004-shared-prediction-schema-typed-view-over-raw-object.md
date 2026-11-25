# The prediction schema is shared, and the typed Prediction is a view over the raw object

The pipeline sends one prediction format: prediction format v4 on the socket, with the same keys the Data API stores, and the Pipeline API passes the object through unchanged. `protocol/schema/prediction.json` types that object once, v4 only and with every field optional, so a later Data API or agent-runtime SDK can reuse it. A `prediction` message keeps the raw object. The typed `Prediction` is built from it, and when its typed fields cannot be read a Job still yields the `Prediction` with the raw object alone.

Not built yet: `protocol/schema/predictionMessage.json` is the `prediction` message schema, and the typed object will land as `prediction.json`. `Prediction` joins the public list in `protocol/public.json` with it.

## Considered options

- **Replace the raw object with typed fields.** One malformed nested value would turn the whole message into `Unknown`, and the prediction would vanish from `predictions()`.
- **Type the object inline in the message schema.** The socket, the Data API and the agent runtime would each end up with their own copy of one format.
- **A closed `depth.semantic` enum.** A generated enum rejects an unknown value, so a new one would fail the whole typed view. The field is an open string, as the `error` code is.
- **Type v1 to v3 as well.** The Pipeline API sets version 4 on every `setSource`, so the older keys never arrive.

## Consequences

- The `prediction` message type is `PredictionMessage`, because `Prediction` names the typed value.
- `objects` nest through an array of itself, which the generator supports in every language. A field that referred directly to its own type would not compile in Rust, and the schema has none.
- Each typed record keeps its raw JSON, so keys the schema does not name, such as `cutouts`, are not lost.
