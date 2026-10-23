using System.Text;
using System.Text.Json;

namespace Bankai.Windows;

// Token spans let us change only selected values, retaining JSONC comments, whitespace,
// unknown properties, UTF-8 text, trailing commas and the original byte-order mark.
internal sealed class JsoncEditor
{
    internal sealed class Node(JsonTokenType type, int start)
    {
        public JsonTokenType Type { get; } = type;
        public int Start { get; } = start;
        public int End { get; set; }
        public Dictionary<string, Node> Properties { get; } = new(StringComparer.Ordinal);
        public List<Node> Items { get; } = [];
        public string? Text { get; set; }
    }

    private readonly byte[] bytes;
    private readonly bool bom;
    private readonly List<(int Start, int End, byte[] Value)> edits = [];
    private readonly Dictionary<Node, List<string>> additions = [];
    public Node Root { get; }

    public JsoncEditor(byte[] source)
    {
        bom = source.AsSpan().StartsWith(new byte[] { 0xef, 0xbb, 0xbf });
        bytes = bom ? source[3..] : source;
        var reader = new Utf8JsonReader(bytes, new JsonReaderOptions
        {
            AllowTrailingCommas = true, CommentHandling = JsonCommentHandling.Skip, MaxDepth = 64,
        });
        if (!reader.Read()) throw new InvalidDataException("Terminal settings are empty.");
        Root = ReadNode(ref reader);
        if (Root.Type != JsonTokenType.StartObject || reader.Read())
            throw new InvalidDataException("Terminal settings must contain one JSON object.");
    }

    private static Node ReadNode(ref Utf8JsonReader reader)
    {
        var node = new Node(reader.TokenType, checked((int)reader.TokenStartIndex));
        if (reader.TokenType == JsonTokenType.StartObject)
        {
            while (reader.Read() && reader.TokenType != JsonTokenType.EndObject)
            {
                var name = reader.GetString()!;
                if (!reader.Read()) throw new JsonException("Missing property value.");
                if (!node.Properties.TryAdd(name, ReadNode(ref reader)))
                    throw new InvalidDataException($"Terminal settings contain duplicate property '{name}'. Resolve it in Terminal before applying a scheme.");
            }
        }
        else if (reader.TokenType == JsonTokenType.StartArray)
        {
            while (reader.Read() && reader.TokenType != JsonTokenType.EndArray)
                node.Items.Add(ReadNode(ref reader));
        }
        else if (reader.TokenType == JsonTokenType.String) node.Text = reader.GetString();
        node.End = checked((int)reader.BytesConsumed);
        return node;
    }

    public void Set(Node owner, string property, object value)
    {
        if (owner.Type != JsonTokenType.StartObject) throw new InvalidDataException("Expected a settings object.");
        var serialized = JsonSerializer.SerializeToUtf8Bytes(value);
        if (owner.Properties.TryGetValue(property, out var previous))
            edits.Add((previous.Start, previous.End, serialized));
        else
        {
            if (!additions.TryGetValue(owner, out var properties)) additions[owner] = properties = [];
            properties.Add(JsonSerializer.Serialize(property) + ": " + Encoding.UTF8.GetString(serialized));
        }
    }

    public void Append(Node array, object value)
    {
        if (array.Type != JsonTokenType.StartArray) throw new InvalidDataException("Expected a settings array.");
        var position = array.Items.Count == 0 ? array.Start + 1 : array.Items[^1].End;
        var prefix = array.Items.Count == 0 ? "" : ",";
        edits.Add((position, position, Encoding.UTF8.GetBytes(prefix + "\n    " + JsonSerializer.Serialize(value))));
    }

    public byte[] Finish()
    {
        foreach (var (owner, properties) in additions)
        {
            var position = owner.Properties.Count == 0 ? owner.Start + 1 : owner.Properties.Last().Value.End;
            var prefix = owner.Properties.Count == 0 ? "" : ",";
            edits.Add((position, position, Encoding.UTF8.GetBytes(prefix + "\n    " + string.Join(",\n    ", properties))));
        }
        using var result = new MemoryStream();
        if (bom) result.Write(new byte[] { 0xef, 0xbb, 0xbf });
        var cursor = 0;
        foreach (var edit in edits.OrderBy(e => e.Start))
        {
            if (edit.Start < cursor) throw new InvalidOperationException("Settings changes overlap.");
            result.Write(bytes.AsSpan(cursor, edit.Start - cursor));
            result.Write(edit.Value);
            cursor = edit.End;
        }
        result.Write(bytes.AsSpan(cursor));
        return result.ToArray();
    }
}
