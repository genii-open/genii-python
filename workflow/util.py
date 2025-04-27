from io import BytesIO
import base64

def plot_to_base64(fig):
    """Convert the matplotlib figure to a base64 string and save it to a file."""
    buffer = BytesIO()
    fig.savefig(buffer, format='png')
    buffer.seek(0)
    data = base64.b64encode(buffer.read()).decode('utf-8')
    buffer.close()
    return "data:image/png;base64,{}".format(data)


# def half_max_amp(evoked: mne.Evoked, tmin=None, tmax=None, include_tmax=True, ch_as_idx=False, t_as_idx=False):
#     # Crop out unwanted datapoints
#     orig_evoked = evoked
#     evoked = evoked.pick("eeg").copy().crop(tmin=tmin, tmax=tmax, include_tmax=include_tmax)
    
#     # Get the channel and time of the max amplitude
#     ch, t = evoked.get_peak()
#     ch_idx = evoked.info["ch_names"].index(ch)
    
#     # this_t_idx is the time index currently being checked
#     this_t_idx = np.where(evoked.times==t)[0][0]
    
#     # Keep track of previous amplitude and current amplitude
#     # initially, prev_amp is out of bound, and this_amp is the max amplitude 
#     prev_amp = float("inf")
#     this_amp = evoked.data[ch_idx, this_t_idx]
    
#     # Calculate half max amplitude
#     half_max_amp = this_amp / 2
    
#     # Start from the peak amplitude, going back in time 
#     # To find the first time index with amplitude smaller than half max
#     while this_amp > half_max_amp and this_t_idx > 0:
#         prev_amp = this_amp
#         this_t_idx -= 1
#         this_amp = evoked.data[ch_idx, this_t_idx]
    
#     # np.argmin(...) return 0 if this_amp is closer to half max amplitude
#     # return 1 if prev_amp is closer
#     # If this_amp is closer, this_t_idx is the time index of half max amplitude
#     # Otherwise, time index of half max amplitude is this_t_idx + 1
#     half_max_t_idx = this_t_idx + np.argmin(np.abs(np.array([this_amp, prev_amp]) - half_max_amp))

#     # Note that half_max_t_idx is relative to the cropped evoked, therefore cannot be used as result directly
#     half_max_t = evoked.times[half_max_t_idx]
    
#     ret_ch = ch_idx if ch_as_idx else ch
#     ret_t = np.where(orig_evoked.times == half_max_t)[0][0] if t_as_idx else half_max_t
    
#     return ret_ch, ret_t
