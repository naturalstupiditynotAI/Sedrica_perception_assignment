"""
Q1: The road disappears - Baseline lane-centre detector
=========================================================

Detects lane centre (u) at two image rows (near/far) using a
white-pixel threshold with a fixed road-width fallback.

Usage:
    python lane_baseline.py

Expects the SeDriCa_perception_starter_data.zip to be unzipped
alongside this script, or edit ZIP_PATH below.
"""
import cv2
import numpy as np
import pandas as pd
import zipfile
import tempfile
import shutil

ZIP_PATH = 'SeDriCa_perception_starter_data.zip'


class LaneBaseline:
    """
    Baseline: white-pixel threshold on single image rows + fixed-width fallback.

    REGION: two full-width pixel rows only (v=260, v=170). No 2-D ROI, no line fit.
    THRESHOLD: grayscale > 190 (lane paint peaks at ~231 in these frames).
    SPLIT: components with centre < W/2 are "left", others "right"; the brightest
           component per half is taken as that boundary.
    FALLBACK: if only one boundary is found, the other is placed ROAD_WIDTH px away.
    ASSUMPTION (WRONG, kept on purpose so Stage 3 can repair it): ROAD_WIDTH=250 px at
           BOTH rows. Measured on the CLEAR images: width(v)=1.054*v-16.3, i.e. 257.7 px
           at v=260 but only 162.9 px at v=170. The 250 is ~right near, ~87 px too wide far.
    UNKNOWN: returned only if no white component exists on the row.

    KNOWN LIMITATIONS found in audit (see edge_case_tests.py; NOT fixed here so the
    baseline stays "unchanged" for the baseline-vs-revision comparison):
      - a 1-px hot pixel or a seam brighter than the paint wins the "brightest" rule
        and is reported with confidence ~0.96;
      - a full-row white blob (overexposure) is accepted as a lane boundary;
      - both boundaries in the same image half -> treated as one boundary;
      - fixed threshold: 0.7x exposure turns every frame into "unknown";
      - confidence uses only paint brightness, so it cannot expose near/far disagreement.
    """

    def __init__(self, white_threshold=190, road_width=250, v_near=260, v_far=170):
        assert v_far < v_near, 'v_far must be a smaller row index (farther ahead) than v_near'
        self.WHITE_THRESHOLD = white_threshold
        self.ROAD_WIDTH = road_width
        self.v_near = v_near
        self.v_far = v_far

    def detect_frame(self, img):
        if img.dtype != np.uint8:
            raise ValueError(f'expected uint8 image in [0,255], got {img.dtype}')
        if img.ndim not in (2, 3) or (img.ndim == 3 and img.shape[2] != 3):
            raise ValueError(f'expected HxW or HxWx3 image, got shape {img.shape}')
        h, w = img.shape[:2]
        if h <= self.v_near:
            raise ValueError(f'image has {h} rows; need > {self.v_near} (frames are 480x320)')
        result = {'u_near': None, 'u_far': None,
                  'confidence_near': 0.0, 'confidence_far': 0.0}

        gray = img if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        white_mask = gray > self.WHITE_THRESHOLD

        if self.v_near < h:
            r = self._detect_at_row(gray, white_mask, self.v_near, w)
            result['u_near'], result['confidence_near'] = r['center'], r['confidence']
        if self.v_far < h:
            r = self._detect_at_row(gray, white_mask, self.v_far, w)
            result['u_far'], result['confidence_far'] = r['center'], r['confidence']
        return result

    def _detect_at_row(self, gray, white_mask, v, width):
        row_mask = white_mask[v, :]
        row_gray = gray[v, :]
        labeled, n = self._label_components(row_mask)

        left_c = right_c = None
        left_i = right_i = 0
        for cid in range(1, n + 1):
            idx = np.where(labeled == cid)[0]
            if len(idx) == 0:
                continue
            center = np.mean(idx)
            intensity = np.mean(row_gray[labeled == cid])
            if center < width / 2:
                if intensity > left_i:
                    left_c, left_i = center, intensity
            else:
                if intensity > right_i:
                    right_c, right_i = center, intensity

        found = (left_c is not None) + (right_c is not None)
        if found == 2:
            conf = min(1.0, (left_i + right_i) / 500.0)
            center = (left_c + right_c) / 2.0
        elif found == 1:
            conf = min(1.0, (left_i + right_i) / 500.0) * 0.7
            if left_c is not None:
                center = (left_c + (left_c + self.ROAD_WIDTH)) / 2.0
            else:
                center = ((right_c - self.ROAD_WIDTH) + right_c) / 2.0
        else:
            center, conf = None, 0.0

        return {'center': center, 'confidence': conf}

    @staticmethod
    def _label_components(mask):
        labeled = np.zeros_like(mask, dtype=np.int32)
        label = 0
        for i in range(len(mask)):
            if mask[i] and labeled[i] == 0:
                label += 1
                LaneBaseline._flood_fill(mask, labeled, i, label)
        return labeled, label

    @staticmethod
    def _flood_fill(mask, labeled, start, label):
        stack = [start]
        while stack:
            i = stack.pop()
            if i < 0 or i >= len(mask) or labeled[i] != 0 or not mask[i]:
                continue
            labeled[i] = label
            stack.append(i + 1)
            stack.append(i - 1)


def run_on_all_frames(zip_path=ZIP_PATH):
    """Step 1 predicts on every frame; Step 2 (after all predictions exist) loads the
    reference CSV, so labels can never influence the detector."""
    temp_dir = tempfile.mkdtemp()
    with zipfile.ZipFile(zip_path, 'r') as z:
        for name in z.namelist():
            if 'city/lane/' in name and name.endswith('.png'):
                z.extract(name, temp_dir)

    detector = LaneBaseline()
    preds = {}
    for seq in ['clear', 'shadow', 'missing']:
        for frame_num in range(24):
            img = cv2.imread(f'{temp_dir}/city/lane/{seq}/{frame_num:03d}.png')
            preds[(seq, frame_num)] = detector.detect_frame(img)

    with zipfile.ZipFile(zip_path, 'r') as z:          # labels loaded only now
        with z.open('city/lane_reference.csv') as f:
            ref_data = pd.read_csv(f)

    rows = []
    for (seq, frame_num), det in preds.items():
        if True:
            ref = ref_data[(ref_data['sequence'] == seq) & (ref_data['frame'] == frame_num)].iloc[0]

            e_near = abs(det['u_near'] - ref['near_center_x_px']) if det['u_near'] is not None else np.nan
            e_far = abs(det['u_far'] - ref['far_center_x_px']) if det['u_far'] is not None else np.nan

            rows.append({
                'sequence': seq, 'frame': frame_num,
                'pred_u_near': det['u_near'], 'pred_u_far': det['u_far'],
                'ref_u_near': ref['near_center_x_px'], 'ref_u_far': ref['far_center_x_px'],
                'error_u_near': e_near, 'error_u_far': e_far,
                'unknown_near': det['u_near'] is None, 'unknown_far': det['u_far'] is None,
                'conf_near': det['confidence_near'], 'conf_far': det['confidence_far'],
            })

    shutil.rmtree(temp_dir)
    return pd.DataFrame(rows)


if __name__ == '__main__':
    df = run_on_all_frames()
    df.to_csv('baseline_results.csv', index=False)
    for seq in ['clear', 'shadow', 'missing']:
        s = df[df.sequence == seq]
        print(f"{seq}: near MAE={s.error_u_near.mean():.2f}px  "
              f"far MAE={s.error_u_far.mean():.2f}px  "
              f"far unknown={100*s.unknown_far.mean():.1f}%")
