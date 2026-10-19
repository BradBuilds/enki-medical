"""
ENKI Pack Loader Integration Example

Demonstrates how to wire the Base-60 renderer to consume
glyphs from the Definition Pack Loader.

This example shows the integration path without modifying
the existing renderer implementation.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.packs import load_pack
from core.validation.render_glyphs import render_decimal_as_base60


def get_glyph_styles_from_pack(pack_path: str) -> dict:
    """
    Load glyph styles from a definition pack.
    
    Args:
        pack_path: Path to the definition pack
        
    Returns:
        Dictionary of glyph styles matching render_glyphs.GLYPH_STYLES format
        
    Example:
        >>> styles = get_glyph_styles_from_pack("libraries/base60")
        >>> print(styles["wedge_ascii"])
        {'unit': '|', 'ten': '<'}
    """
    result = load_pack(pack_path)
    
    if not result.ok:
        raise ValueError(f"Failed to load pack: {result.errors}")
    
    # Find the glyphs definition
    glyphs_defs = result.index.by_type.get("glyphs", [])
    if not glyphs_defs:
        raise ValueError("No glyph definitions found in pack")
    
    # Get first glyphs definition (Base-60 has one)
    glyphs_def = glyphs_defs[0]
    
    # Extract glyph styles from content
    return glyphs_def.content.get("styles", {})


def render_using_pack(value: int, pack_path: str = "libraries/base60") -> str:
    """
    Render a decimal value using glyphs from a definition pack.
    
    This demonstrates the integration pattern:
    1. Load pack via pack loader
    2. Extract glyph definitions
    3. Pass to renderer
    
    Args:
        value: Decimal value to render
        pack_path: Path to the definition pack
        
    Returns:
        Base-60 glyph representation
        
    Example:
        >>> render_using_pack(3723)
        '| || |||'
    """
    # Load pack
    result = load_pack(pack_path)
    
    if not result.ok:
        raise ValueError(f"Pack load failed: {result.errors}")
    
    # Verify system definition
    system_def = result.index.by_id.get("base60.system")
    if not system_def:
        raise ValueError("No system definition found")
    
    # Verify base is 60
    base = system_def.content.get("base")
    if base != 60:
        raise ValueError(f"Expected base 60, got {base}")
    
    # Render using existing renderer
    # (In production, the renderer would be updated to accept
    #  glyph styles from the pack loader)
    result = render_decimal_as_base60(value)
    return result["glyphs"]


def demonstrate_pack_integration():
    """
    Demonstrate the full integration workflow.
    
    This shows how the pack loader provides the foundation
    for definition-driven rendering.
    """
    print("=" * 60)
    print("ENKI Pack Loader Integration Demo")
    print("=" * 60)
    print()
    
    # Load Base-60 pack
    print("Loading Base-60 pack...")
    result = load_pack("libraries/base60")
    
    if result.ok:
        print(f"✅ Pack loaded: {result.pack_id} v{result.version['version']}")
        print(f"   Definitions: {result.definition_count()}")
        print()
        
        # Show loaded definitions
        print("Loaded definitions:")
        for def_id in sorted(result.index.by_id.keys()):
            definition = result.index.by_id[def_id]
            print(f"  - {def_id:20s} [{definition.type}]")
        print()
        
        # Extract glyph styles
        print("Extracting glyph styles...")
        styles = get_glyph_styles_from_pack("libraries/base60")
        print(f"✅ Found {len(styles)} glyph style(s)")
        print()
        
        # Show available styles
        print("Available styles:")
        for style_name, glyphs in styles.items():
            print(f"  {style_name}: {glyphs}")
        print()
        
        # Render examples
        print("Rendering examples:")
        test_values = [0, 1, 59, 60, 3723]
        for value in test_values:
            rendered = render_using_pack(value)
            print(f"  {value:5d} → {rendered}")
        print()
        
        print("=" * 60)
        print("✅ Integration successful!")
        print("=" * 60)
    else:
        print(f"❌ Pack load failed:")
        for error in result.errors:
            print(f"  - {error}")


if __name__ == "__main__":
    demonstrate_pack_integration()
