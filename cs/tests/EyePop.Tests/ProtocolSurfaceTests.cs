using Xunit;

namespace EyePop.Tests;

public class ProtocolSurfaceTests
{
    // The tests see the assembly's internals, so only the exported types say what a caller can name.
    [Fact]
    public void The_generated_public_surface_is_the_public_list_and_what_it_holds()
    {
        var exported = typeof(Client).Assembly.GetExportedTypes()
            .Where(type => type.Namespace == "EyePop.Protocol")
            .Select(type => type.Name)
            .Order(StringComparer.Ordinal);

        Assert.Equal(
            new[]
            {
                "Ability", "Camera", "CameraDistortion", "CameraExtrinsics", "CameraExtrinsicsRotation",
                "CameraExtrinsicsTranslation", "CameraIntrinsics", "ComponentParams", "Contour", "Depth",
                "Dropped", "End", "EndReason", "EndReasonWire", "InferenceComponent", "JobMessage", "Mask",
                "Point", "Pop", "PopComponent", "PopDepthMap", "PredictedClass", "PredictedKeyPoint",
                "PredictedKeyPoints", "PredictedMesh", "PredictedObject", "PredictedText", "Prediction",
                "PredictionMessage", "RawComponent", "Roi", "RoiContour", "RoiContourPoint", "RoiRectangle",
                "SourceDefaults", "Start", "TrackEvent", "Usage",
            },
            exported);
    }
}
