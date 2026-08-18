#!/usr/bin/env python
from __future__ import annotations
import argparse, csv, tempfile
from pathlib import Path
from ai_video_production.dbd_vision_slices import FFmpegSliceExtractor, ReferenceSliceIndex


def main() -> int:
    p=argparse.ArgumentParser(description='Build TASK-049 DbD labeled slice reference index')
    p.add_argument('--csv', required=True, help='CSV columns: label,image_path[,group]')
    p.add_argument('--index-id', required=True); p.add_argument('--output', required=True); p.add_argument('--ffmpeg', default='ffmpeg')
    args=p.parse_args(); rows=[]
    with Path(args.csv).open(encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            if not row.get('label') or not row.get('image_path'): raise SystemExit('CSV requires label and image_path')
            rows.append(row)
    if not rows: raise SystemExit('CSV has no samples')
    extractor=FFmpegSliceExtractor(args.ffmpeg)
    with tempfile.TemporaryDirectory(prefix='bvp-dbd-slices-') as td:
        samples=[]
        for i,row in enumerate(rows):
            out=Path(td)/f'{i:06d}.pgm'; extractor.normalize_still_to_pgm(image_path=row['image_path'],output_path=out)
            samples.append((row['label'].strip(), out, (row.get('group') or 'default').strip() or 'default'))
        index=ReferenceSliceIndex.train_from_pgm(index_id=args.index_id,samples=samples)
        index.save(args.output)
    print(f'[PASS] {args.output} references={len(index.references)}')
    return 0
if __name__=='__main__': raise SystemExit(main())
