using Xunit;

namespace EyePop.Tests;

public class EyePopExceptionTests
{
    [Fact]
    public void It_carries_the_kind_and_the_fields_that_apply()
    {
        var error = new EyePopException(ErrorKind.Closed, "closed", closeCode: 1008, error: "unexpected_bytes");

        Assert.Equal(ErrorKind.Closed, error.Kind);
        Assert.Equal(1008, error.CloseCode);
        Assert.Equal("unexpected_bytes", error.Error);
        Assert.Null(error.Status);
    }
}
