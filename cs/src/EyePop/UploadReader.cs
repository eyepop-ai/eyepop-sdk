namespace EyePop;

/// <summary>
/// Reads one upload's content for the shell, remembering where it stopped. The core asks for 64 KiB at a
/// time as credit arrives, and a stream is read once, so the position has to live here. One reader serves
/// one send of an upload: a source sent again after a reconnect gets a new reader and a new stream.
/// </summary>
internal sealed class UploadReader : IDisposable
{
    private readonly UploadContent _content;
    private Stream? _stream;
    private int _offset;

    public UploadReader(string jobId, UploadContent content)
    {
        JobId = jobId;
        _content = content;
    }

    public string JobId { get; }

    /// <summary>Up to <paramref name="count"/> bytes, or all of them when <paramref name="whole"/>. Last is true once the content ended.</summary>
    public async Task<(ReadOnlyMemory<byte> Data, bool Last)> ReadAsync(long count, bool whole, CancellationToken ct)
    {
        if (_content is UploadContent.BytesContent bytes)
        {
            var take = whole ? bytes.Bytes.Length - _offset : (int)Math.Min(count, bytes.Bytes.Length - _offset);
            var slice = bytes.Bytes.Slice(_offset, take);
            _offset += take;
            return (slice, _offset >= bytes.Bytes.Length);
        }

        _stream ??= ((UploadContent.StreamContent)_content).Open();
        var buffer = new MemoryStream();
        if (whole)
        {
            await _stream.CopyToAsync(buffer, ct).ConfigureAwait(false);
            return (buffer.ToArray(), true);
        }
        var chunk = new byte[count];
        var filled = 0;
        while (filled < chunk.Length)
        {
            var read = await _stream.ReadAsync(chunk.AsMemory(filled), ct).ConfigureAwait(false);
            if (read == 0)
            {
                return (chunk.AsMemory(0, filled), true);
            }
            filled += read;
        }
        return (chunk, false);
    }

    public void Dispose() => _stream?.Dispose();
}
