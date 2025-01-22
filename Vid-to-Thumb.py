import cv2
import os
import argparse
import re
from datetime import timedelta
import sys

def calculate_frame_number(cap, frame_option):
    """ フレーム番号を計算 """
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    if isinstance(frame_option, int):
        return min(max(frame_option, 0), total_frames-1)
    elif frame_option.startswith('t+'):
        time_str = frame_option[2:]
        try:
            time_obj = timedelta(**parse_time(time_str))
            target_sec = time_obj.total_seconds()
            return min(int(target_sec * fps), total_frames-1)
        except:
            print(f"無効な時間形式: {time_str}")
            return 0
    else:
        print(f"無効なフレーム指定: {frame_option}")
        return 0

def parse_time(time_str):
    """ 時間文字列をパース """
    parts = {'hours': 0, 'minutes': 0, 'seconds': 0}
    units = {'h': 'hours', 'm': 'minutes', 's': 'seconds'}
    
    current_value = ''
    for char in time_str:
        if char.isdigit():
            current_value += char
        elif char in units:
            parts[units[char]] = int(current_value)
            current_value = ''
    if current_value:
        parts['seconds'] = int(current_value)
    return parts

def apply_regex_pattern(original, pattern, frame_num, time_pos):
    """ 強化版正規表現処理関数 """
    replacements = {
        '{n}': original,
        '{f}': f"{frame_num:06d}",
        '{t}': time_pos,
        '{n.base}': os.path.splitext(original)[0],
        '{n.digits}': ''.join(filter(str.isdigit, original)),
        '{n.letters}': ''.join(filter(str.isalpha, original)),
    }

    def regex_replacer(match):
        command = match.group(1)
        
        if ':' in command:
            parts = command.split(':')
            if parts[0] == 'n' and parts[1].isdigit():
                return original[:int(parts[1])]
        
        if command.startswith('n.match('):
            regex = command[8:-1]
            matched = re.search(regex, original)
            if matched:
                return matched.group()
            return ''
            
        if command.startswith('n.replace('):
            args = command[10:-1].split(',', 1)
            return original.replace(args[0], args[1])
            
        return match.group(0)

    try:
        for k, v in replacements.items():
            pattern = pattern.replace(k, v)
        
        pattern = re.sub(r'{(\w+\.\w+)}', regex_replacer, pattern)
        pattern = re.sub(r'{(\w+:[^}]+)}', regex_replacer, pattern)
        pattern = re.sub(r'{(n\.match\([^}]+\))}', regex_replacer, pattern)
        pattern = re.sub(r'{(n\.replace\([^}]+\))}', regex_replacer, pattern)
        
        return pattern
    
    except Exception as e:
        print(f"パターン処理エラー: {str(e)}")
        return f"{original}_error"

def extract_frame(video_path, frame_option, output_format, output_dir, name_pattern=None, keep_original_name=False):
    """ フレームを抽出して保存 """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"エラー: {video_path} を開けません")
        return

    try:
        # フレーム番号計算
        frame_number = calculate_frame_number(cap, frame_option)
        
        # FPSを取得（キャプチャオブジェクトが開いている状態で）
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            print(f"警告: FPS情報が不正なため、デフォルトの30 FPSを使用します")
            fps = 30.0

        # フレーム位置を設定
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        success, frame = cap.read()

        if not success:
            print(f"警告: {video_path} からフレーム {frame_number} を読み込めません")
            return

        # 時間位置の計算
        time_position = f"{frame_number / fps:.2f}s"

        # ファイル名生成
        original_name = os.path.splitext(os.path.basename(video_path))[0]
        
        if keep_original_name:
            filename = original_name
        elif name_pattern:
            filename = apply_regex_pattern(original_name, name_pattern, frame_number, time_position)
        else:
            filename = f"{original_name}_f{frame_number:06d}_{time_position}"

        # 出力パスの生成
        output_path = os.path.join(output_dir, f"{filename}.{output_format}")
        output_path = avoid_overwrite(output_path)
        
        cv2.imwrite(output_path, frame)
        print(f"保存成功: {output_path}")

    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
    finally:
        cap.release()

def avoid_overwrite(path):
    """ ファイル重複を防ぐ """
    counter = 1
    base, ext = os.path.splitext(path)
    while os.path.exists(path):
        path = f"{base}_{counter}{ext}"
        counter += 1
    return path

def process_videos(input_path, frame_option, output_format, output_dir, name_pattern=None, keep_original_name=False):
    """ 複数ファイル処理のメイン関数 """
    if os.path.isdir(input_path):
        files = [os.path.join(input_path, f) for f in os.listdir(input_path) 
                if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv'))]
    else:
        files = [input_path]

    os.makedirs(output_dir, exist_ok=True)

    for video_path in files:
        extract_frame(
            video_path,
            frame_option,
            output_format,
            output_dir,
            name_pattern,
            keep_original_name
        )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='高度な動画フレーム抽出ツール')
    parser.add_argument('input', help='動画ファイルまたはディレクトリのパス')
    parser.add_argument('-f', '--format', default='jpg', help='出力画像形式（デフォルト: jpg）')
    parser.add_argument('-o', '--output', default='./thumbnails', help='出力ディレクトリ（デフォルト: ./thumbnails）')
    parser.add_argument('-n', '--frame', type=lambda x: int(x) if x.isdigit() else x, 
                       default=0, help='フレーム指定（数値またはt+時間）')
    parser.add_argument('--name', help='カスタム命名パターン')
    parser.add_argument('--original-name', action='store_true', help='元のファイル名をそのまま使用')
    
    args = parser.parse_args()
    
    if args.original_name and args.name:
        print("警告: --original-name と --name は同時に指定できません")
        exit(1)

    process_videos(
        args.input,
        args.frame,
        args.format,
        args.output,
        name_pattern=args.name,
        keep_original_name=args.original_name
    )